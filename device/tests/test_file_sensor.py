import sys
import tempfile
import unittest
from pathlib import Path

DEVICE_ROOT = Path(__file__).resolve().parents[1]
if str(DEVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(DEVICE_ROOT))

from smart_inventory.sensors.file_sensor import FileSensor  # noqa: E402


class TestFileSensor(unittest.TestCase):
    def test_missing_or_invalid_file_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / "missing.txt"
            sensor = FileSensor(sensor_id="missing", path=str(missing_path))
            self.assertEqual(sensor.read(), (None, None))

            empty_path = Path(temp_dir) / "empty.txt"
            empty_path.write_text("", encoding="utf-8")
            empty_sensor = FileSensor(sensor_id="empty", path=str(empty_path))
            self.assertEqual(empty_sensor.read(), (None, None))

            invalid_path = Path(temp_dir) / "invalid.txt"
            invalid_path.write_text("not-a-number", encoding="utf-8")
            invalid_sensor = FileSensor(sensor_id="invalid", path=str(invalid_path))
            self.assertEqual(invalid_sensor.read(), (None, None))

    def test_digital_mode_maps_to_binary_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sensor_path = Path(temp_dir) / "digital.txt"
            sensor_path.write_text("0", encoding="utf-8")
            sensor = FileSensor(sensor_id="digital", path=str(sensor_path), mode="digital")
            self.assertEqual(sensor.read(), (0.0, 0.0))

            sensor_path.write_text("5", encoding="utf-8")
            self.assertEqual(sensor.read(), (1.0, 1.0))

    def test_analog_mode_scales_and_tares(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sensor_path = Path(temp_dir) / "analog.txt"
            sensor_path.write_text("12.5", encoding="utf-8")
            sensor = FileSensor(
                sensor_id="analog",
                path=str(sensor_path),
                mode="analog",
                scale_factor=2.5,
                tare_offset=2.5,
            )
            self.assertEqual(sensor.read(), (12.5, 4.0))
