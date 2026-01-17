import argparse
import datetime as dt
import logging
import os
import signal
import time
from typing import Dict

from smart_inventory.config import AppConfig, load_config
from smart_inventory.processing import SensorProcessor
from smart_inventory.queue import ReadingQueue
from smart_inventory.sensors import create_sensor
from smart_inventory.transport import TransportError, post_readings_batch


class DeviceService:
    def __init__(self, config: AppConfig) -> None:
        self._config = config
        self._queue = ReadingQueue(config.storage.queue_db_path)
        self._sensors = []
        self._processors: Dict[str, SensorProcessor] = {}
        self._stop = False
        self._last_flush = 0.0
        self._next_retry_at = 0.0
        self._retry_delay = 1.0

        for sensor_cfg in config.sensors:
            try:
                sensor = create_sensor(
                    sensor_type=sensor_cfg.sensor_type,
                    sensor_id=sensor_cfg.sensor_id,
                    params=sensor_cfg.params,
                )
            except Exception as exc:  # noqa: BLE001 - we want to log and continue
                logging.error("Sensor %s failed to initialize: %s", sensor_cfg.sensor_id, exc)
                continue

            report_on_change = sensor_cfg.effective_report_on_change(config.runtime)
            processor = SensorProcessor(
                sensor_id=sensor_cfg.sensor_id,
                mode=sensor_cfg.effective_mode(),
                debounce_ms=sensor_cfg.debounce_ms,
                thresholds=sensor_cfg.thresholds,
                state_map=sensor_cfg.state_map,
                report_on_change_only=report_on_change,
            )
            self._sensors.append(sensor)
            self._processors[sensor_cfg.sensor_id] = processor

        if not self._sensors:
            raise RuntimeError("No sensors initialized")

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        logging.info("Smart Inventory device service starting")
        poll_interval = max(0.05, self._config.runtime.poll_interval_ms / 1000.0)

        while not self._stop:
            loop_start = time.time()
            timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
            for sensor in self._sensors:
                raw, normalized = sensor.read()
                if raw is None or normalized is None:
                    continue
                processor = self._processors.get(sensor.sensor_id)
                if processor is None:
                    continue
                reading = processor.process(raw, normalized, loop_start, timestamp)
                if reading:
                    self._queue.enqueue(reading)

            self._flush(loop_start)
            elapsed = time.time() - loop_start
            sleep_for = max(0.0, poll_interval - elapsed)
            time.sleep(sleep_for)

        logging.info("Smart Inventory device service stopped")

    def _flush(self, now: float) -> None:
        if now < self._next_retry_at:
            return

        pending = self._queue.pending_count()
        if pending == 0:
            return

        if pending < self._config.network.batch_size:
            if now - self._last_flush < self._config.network.flush_interval_seconds:
                return

        batch = self._queue.get_batch(self._config.network.batch_size)
        if not batch:
            return

        payload = {
            "device_id": self._config.device.device_id,
            "firmware": self._config.device.firmware,
            "sent_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "readings": batch,
        }

        try:
            response = post_readings_batch(
                base_url=self._config.network.base_url,
                payload=payload,
                api_token=self._config.network.api_token,
                ca_cert_path=self._config.network.ca_cert_path,
                timeout_seconds=self._config.network.timeout_seconds(),
            )
        except TransportError as exc:
            logging.warning("Upload failed: %s", exc)
            self._schedule_retry(now)
            return

        ack_seq = response.get("ack_seq_id")
        if ack_seq is None and batch:
            ack_seq = batch[-1]["seq_id"]
        if ack_seq is not None:
            self._queue.ack_upto(int(ack_seq))
        self._last_flush = now
        self._retry_delay = 1.0

    def _schedule_retry(self, now: float) -> None:
        self._next_retry_at = now + self._retry_delay
        self._retry_delay = min(
            self._retry_delay * 2,
            float(self._config.network.retry_max_seconds),
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smart Inventory device service")
    parser.add_argument(
        "--config",
        default=None,
        help="Path to config JSON (or SMART_INVENTORY_CONFIG)",
    )
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    config_path = args.config or os.getenv("SMART_INVENTORY_CONFIG")
    if not config_path:
        raise SystemExit("Config path required via --config or SMART_INVENTORY_CONFIG")

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )

    config = load_config(config_path)
    service = DeviceService(config)

    def _handle_signal(_signum, _frame) -> None:
        service.stop()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    service.run()


if __name__ == "__main__":
    main()
