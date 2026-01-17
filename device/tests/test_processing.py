import sys
import unittest
from pathlib import Path

DEVICE_ROOT = Path(__file__).resolve().parents[1]
if str(DEVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(DEVICE_ROOT))

from smart_inventory.processing import (  # noqa: E402
    Debouncer,
    EMAFilter,
    MedianFilter,
    SensorProcessor,
    evaluate_threshold,
)


class TestDebouncer(unittest.TestCase):
    def test_debounce_sequence(self) -> None:
        debouncer = Debouncer(100)

        self.assertEqual(debouncer.update(1, now=0.0), 1)
        self.assertIsNone(debouncer.update(1, now=0.02))
        self.assertIsNone(debouncer.update(0, now=0.05))
        self.assertIsNone(debouncer.update(0, now=0.15))
        self.assertEqual(debouncer.update(0, now=0.21), 0)


class TestMedianFilter(unittest.TestCase):
    def test_even_window_uses_upper_middle(self) -> None:
        median = MedianFilter(window_size=5)

        self.assertEqual(median.update(10), 10)
        self.assertEqual(median.update(1), 10)
        self.assertEqual(median.update(7), 7)

    def test_zero_window_defaults_to_one(self) -> None:
        median = MedianFilter(window_size=0)

        self.assertEqual(median.update(9), 9)
        self.assertEqual(median.update(3), 3)


class TestEMAFilter(unittest.TestCase):
    def test_exponential_smoothing(self) -> None:
        ema = EMAFilter(alpha=0.5)

        self.assertEqual(ema.update(10), 10)
        self.assertAlmostEqual(ema.update(20), 15.0)
        self.assertAlmostEqual(ema.update(16), 15.5)


class TestEvaluateThreshold(unittest.TestCase):
    def test_missing_thresholds_returns_last_or_ok(self) -> None:
        self.assertEqual(evaluate_threshold(5, {}, None), "ok")
        self.assertEqual(evaluate_threshold(5, {"low": 10}, "low"), "low")

    def test_invalid_threshold_range_falls_back(self) -> None:
        self.assertEqual(
            evaluate_threshold(5, {"low": 10, "ok": 10}, None),
            "ok",
        )
        self.assertEqual(
            evaluate_threshold(5, {"low": 10, "ok": 10}, "low"),
            "low",
        )

    def test_hysteresis_and_boundaries(self) -> None:
        thresholds = {"low": 10, "ok": 20}

        self.assertEqual(evaluate_threshold(5, thresholds, None), "low")
        self.assertEqual(evaluate_threshold(15, thresholds, None), "low")
        self.assertEqual(evaluate_threshold(15, thresholds, "ok"), "ok")
        self.assertEqual(evaluate_threshold(15, thresholds, "low"), "low")
        self.assertEqual(evaluate_threshold(25, thresholds, "low"), "ok")


class TestSensorProcessor(unittest.TestCase):
    def test_digital_sensor_debounce_and_state_map(self) -> None:
        processor = SensorProcessor(
            sensor_id="door-1",
            mode="digital",
            debounce_ms=100,
            thresholds=None,
            state_map={"on": "open", "off": "closed"},
            report_on_change_only=True,
        )

        first = processor.process(
            raw_value=1.0,
            normalized_value=1.0,
            now=0.0,
            ts_iso="2026-01-17T00:00:00Z",
        )
        self.assertEqual(
            first,
            {
                "sensor_id": "door-1",
                "ts": "2026-01-17T00:00:00Z",
                "raw_value": 1.0,
                "normalized_value": 1.0,
                "state": "open",
            },
        )

        self.assertIsNone(
            processor.process(
                raw_value=1.0,
                normalized_value=1.0,
                now=0.02,
                ts_iso="2026-01-17T00:00:01Z",
            )
        )
        self.assertIsNone(
            processor.process(
                raw_value=0.0,
                normalized_value=0.0,
                now=0.05,
                ts_iso="2026-01-17T00:00:02Z",
            )
        )

        second = processor.process(
            raw_value=0.0,
            normalized_value=0.0,
            now=0.16,
            ts_iso="2026-01-17T00:00:03Z",
        )
        self.assertEqual(
            second,
            {
                "sensor_id": "door-1",
                "ts": "2026-01-17T00:00:03Z",
                "raw_value": 0.0,
                "normalized_value": 0.0,
                "state": "closed",
            },
        )

    def test_analog_sensor_reports_on_change_only(self) -> None:
        processor = SensorProcessor(
            sensor_id="bin-1",
            mode="analog",
            debounce_ms=0,
            thresholds={"low": 10, "ok": 20},
            state_map=None,
            report_on_change_only=True,
        )

        first = processor.process(
            raw_value=5.0,
            normalized_value=5.0,
            now=0.0,
            ts_iso="2026-01-17T00:00:10Z",
        )
        self.assertEqual(
            first,
            {
                "sensor_id": "bin-1",
                "ts": "2026-01-17T00:00:10Z",
                "raw_value": 5.0,
                "normalized_value": 5.0,
                "state": "low",
            },
        )

        second = processor.process(
            raw_value=50.0,
            normalized_value=50.0,
            now=1.0,
            ts_iso="2026-01-17T00:00:11Z",
        )
        self.assertEqual(
            second,
            {
                "sensor_id": "bin-1",
                "ts": "2026-01-17T00:00:11Z",
                "raw_value": 50.0,
                "normalized_value": 50.0,
                "state": "ok",
            },
        )

        self.assertIsNone(
            processor.process(
                raw_value=15.0,
                normalized_value=15.0,
                now=2.0,
                ts_iso="2026-01-17T00:00:12Z",
            )
        )

    def test_analog_sensor_reports_every_sample_when_enabled(self) -> None:
        processor = SensorProcessor(
            sensor_id="bin-2",
            mode="analog",
            debounce_ms=0,
            thresholds={"low": 10, "ok": 20},
            state_map=None,
            report_on_change_only=False,
        )

        first = processor.process(
            raw_value=12.0,
            normalized_value=12.0,
            now=0.0,
            ts_iso="2026-01-17T00:01:00Z",
        )
        self.assertIsNotNone(first)
        self.assertEqual(first["state"], "low")

        second = processor.process(
            raw_value=13.0,
            normalized_value=13.0,
            now=1.0,
            ts_iso="2026-01-17T00:01:01Z",
        )
        self.assertIsNotNone(second)
        self.assertEqual(second["state"], "low")
