"""One Bluetooth connection setup at a time per process (ble_cx._setup_lock)."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from meshcore.ble_cx import BLEConnection
from meshcore.connection_manager import ConnectionManager
from meshcore.events import EventType


def slow_client(log, name):
    client = MagicMock()

    async def connect():
        log.append((name, "start"))
        await asyncio.sleep(0.05)
        log.append((name, "end"))

    client.connect = AsyncMock(side_effect=connect)
    client.start_notify = AsyncMock()
    client.is_connected = True
    service = MagicMock()
    service.get_characteristic.return_value = MagicMock()
    client.services.get_service.return_value = service
    return client


class TestSetupLock(unittest.TestCase):
    @patch("meshcore.ble_cx.BleakClient")
    def test_two_setups_do_not_overlap(self, bleak_client):
        log = []
        bleak_client.side_effect = [slow_client(log, "a"), slow_client(log, "b")]

        async def both():
            a = BLEConnection(address="00:11:22:33:44:55")
            b = BLEConnection(address="66:77:88:99:AA:BB")
            return await asyncio.gather(a.connect(), b.connect())

        results = asyncio.run(both())
        self.assertEqual(results, ["00:11:22:33:44:55", "66:77:88:99:AA:BB"])
        self.assertEqual(log, [("a", "start"), ("a", "end"), ("b", "start"), ("b", "end")])


class TestReconnectingEvent(unittest.TestCase):
    def test_drop_emits_reconnecting_then_connected(self):
        async def run():
            connection = MagicMock()
            connection.connect = AsyncMock(return_value="addr")
            dispatcher = MagicMock()
            dispatcher.dispatch = AsyncMock()
            manager = ConnectionManager(connection, dispatcher, auto_reconnect=True, max_reconnect_attempts=3)
            await manager.connect()
            await manager.handle_disconnect("ble_disconnect")
            await manager._reconnect_task
            return [call.args[0].type for call in dispatcher.dispatch.call_args_list]

        types = asyncio.run(run())
        self.assertEqual(types, [EventType.CONNECTED, EventType.RECONNECTING, EventType.CONNECTED])


if __name__ == "__main__":
    unittest.main()
