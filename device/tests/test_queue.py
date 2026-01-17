import sys
import tempfile
import unittest
from pathlib import Path

DEVICE_ROOT = Path(__file__).resolve().parents[1]
if str(DEVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(DEVICE_ROOT))

from smart_inventory.queue import ReadingQueue  # noqa: E402


class TestReadingQueue(unittest.TestCase):
    def test_enqueue_batch_and_ack(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "queue.db"
            queue = ReadingQueue(str(db_path))

            try:
                first_id = queue.enqueue(
                    {
                        "sensor_id": "sensor-1",
                        "ts": "2026-01-17T00:10:00Z",
                        "raw_value": 1.0,
                        "normalized_value": 1.0,
                        "state": "ok",
                    }
                )
                second_id = queue.enqueue(
                    {
                        "sensor_id": "sensor-2",
                        "ts": "2026-01-17T00:10:01Z",
                        "raw_value": 0.0,
                        "normalized_value": 0.0,
                        "state": "low",
                    }
                )

                self.assertEqual(first_id, 1)
                self.assertEqual(second_id, 2)
                self.assertEqual(queue.pending_count(), 2)
                self.assertEqual(queue.max_seq_id(), 2)

                batch = queue.get_batch(limit=10)
                self.assertEqual([item["seq_id"] for item in batch], [1, 2])

                queue.ack_upto(1)
                self.assertEqual(queue.pending_count(), 1)
                self.assertEqual(queue.max_seq_id(), 2)

                remaining = queue.get_batch(limit=10)
                self.assertEqual([item["seq_id"] for item in remaining], [2])

                queue.ack_upto(2)
                self.assertEqual(queue.pending_count(), 0)
                self.assertIsNone(queue.max_seq_id())
            finally:
                queue._conn.close()
