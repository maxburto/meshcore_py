"""PUSH_CODE_LOG_RX_KEPT (0x91): a heard packet the radio kept while no client could take it."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from meshcore.events import EventType
from meshcore.reader import MessageReader

RAW = bytes.fromhex("0987769268362c3aa55e72d2773ebeef97b61760")


def dispatched(frame):
    dispatcher = MagicMock()
    dispatcher.dispatch = AsyncMock()
    reader = MessageReader(dispatcher)
    asyncio.run(reader.handle_rx(bytearray(frame)))
    return [call.args[0] for call in dispatcher.dispatch.call_args_list]


class TestRxLogKept(unittest.TestCase):
    def test_kept_frame_gives_heard_time_and_drops(self):
        frame = bytes([0x91, 0xEF, 0xB1]) + (1762581318).to_bytes(4, "little") + (3).to_bytes(2, "little") + RAW
        events = [e for e in dispatched(frame) if e.type == EventType.RX_LOG_KEPT]
        self.assertEqual(len(events), 1)
        p = events[0].payload
        self.assertEqual(p["heard_at"], 1762581318)
        self.assertEqual(p["dropped_before"], 3)
        self.assertEqual(p["snr"], -4.25)
        self.assertEqual(p["rssi"], -79)
        self.assertEqual(p["payload"], RAW.hex())

    def test_live_frame_unchanged(self):
        frame = bytes([0x88, 0xEF, 0xB1]) + RAW
        events = [e for e in dispatched(frame) if e.type in (EventType.RX_LOG_DATA, EventType.RX_LOG_KEPT)]
        self.assertEqual([e.type for e in events], [EventType.RX_LOG_DATA])
        self.assertEqual(events[0].payload["payload"], RAW.hex())
        self.assertNotIn("heard_at", events[0].payload)


if __name__ == "__main__":
    unittest.main()
