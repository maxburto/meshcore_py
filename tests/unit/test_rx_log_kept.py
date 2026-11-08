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
    def test_kept_frame_gives_age_and_drops(self):
        frame = bytes([0x91, 0xEF, 0xB1]) + (1762581318).to_bytes(4, "little") + (3).to_bytes(2, "little") + RAW
        events = [e for e in dispatched(frame) if e.type == EventType.RX_LOG_KEPT]
        self.assertEqual(len(events), 1)
        p = events[0].payload
        self.assertEqual(p["age_ms"], 1762581318)
        self.assertEqual(p["dropped_before"], 3)
        self.assertEqual(p["snr"], -4.25)
        self.assertEqual(p["rssi"], -79)
        self.assertEqual(p["payload"], RAW.hex())

    def test_live_frame_unchanged(self):
        frame = bytes([0x88, 0xEF, 0xB1]) + RAW
        events = [e for e in dispatched(frame) if e.type in (EventType.RX_LOG_DATA, EventType.RX_LOG_KEPT)]
        self.assertEqual([e.type for e in events], [EventType.RX_LOG_DATA])
        self.assertEqual(events[0].payload["payload"], RAW.hex())
        self.assertNotIn("age_ms", events[0].payload)


def long_parts(raw, flags=1, age=7, dropped=0, first=164):
    def part(off, chunk):
        return (
            bytes([0x92, 0xEF, 0xB1]) + age.to_bytes(4, "little") + dropped.to_bytes(2, "little")
            + bytes([flags, len(raw), off]) + chunk
        )
    return [part(0, raw[:first]), part(first, raw[first:])]


def fed(frames):
    dispatcher = MagicMock()
    dispatcher.dispatch = AsyncMock()
    reader = MessageReader(dispatcher)
    for frame in frames:
        asyncio.run(reader.handle_rx(bytearray(frame)))
    return [c.args[0] for c in dispatcher.dispatch.call_args_list
            if c.args[0].type in (EventType.RX_LOG_DATA, EventType.RX_LOG_KEPT)]


LONG = bytes(range(255))


class TestRxLogLong(unittest.TestCase):
    def test_live_long_packet_arrives_whole_as_heard_now(self):
        events = fed(long_parts(LONG))
        self.assertEqual([e.type for e in events], [EventType.RX_LOG_DATA])
        self.assertEqual(events[0].payload["payload"], LONG.hex())
        self.assertEqual(events[0].payload["payload_length"], 255)
        self.assertEqual(events[0].payload["rssi"], -79)

    def test_kept_long_packet_keeps_its_age(self):
        events = fed(long_parts(LONG, flags=0, age=9000, dropped=2))
        self.assertEqual([e.type for e in events], [EventType.RX_LOG_KEPT])
        self.assertEqual(events[0].payload["age_ms"], 9000)
        self.assertEqual(events[0].payload["dropped_before"], 2)
        self.assertEqual(events[0].payload["payload"], LONG.hex())

    def test_nothing_before_the_last_part(self):
        self.assertEqual(fed(long_parts(LONG)[:1]), [])

    def test_last_part_without_the_first_is_given_up(self):
        self.assertEqual(fed(long_parts(LONG)[1:]), [])

    def test_resent_from_its_start_after_a_drop_arrives_once(self):
        first, second = long_parts(LONG)
        events = fed([first, first, second])
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload["payload"], LONG.hex())

    def test_next_packet_after_a_lost_part_is_whole(self):
        first, _ = long_parts(LONG)
        other = long_parts(bytes(reversed(LONG)))
        events = fed([first] + other)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].payload["payload"], bytes(reversed(LONG)).hex())


if __name__ == "__main__":
    unittest.main()
