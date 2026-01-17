import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


def _resolve_env(value: Any) -> Any:
    if isinstance(value, str) and value.startswith("env:"):
        env_key = value.split(":", 1)[1]
        return os.getenv(env_key)
    return value


def _resolve_obj(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_obj(val) for key, val in value.items()}
    if isinstance(value, list):
        return [_resolve_obj(item) for item in value]
    return _resolve_env(value)


@dataclass
class DeviceConfig:
    device_id: str
    location: Optional[str] = None
    firmware: str = "0.1.0"


@dataclass
class NetworkConfig:
    base_url: str
    api_token: Optional[str] = None
    ca_cert_path: Optional[str] = None
    batch_size: int = 25
    flush_interval_seconds: int = 15
    retry_max_seconds: int = 300
    connect_timeout_seconds: int = 5
    read_timeout_seconds: int = 10

    def timeout_seconds(self) -> int:
        return max(self.connect_timeout_seconds, self.read_timeout_seconds)


@dataclass
class StorageConfig:
    queue_db_path: str


@dataclass
class RuntimeConfig:
    poll_interval_ms: int = 200
    report_on_change_only: bool = True


@dataclass
class SensorConfig:
    sensor_id: str
    sensor_type: str
    mode: Optional[str] = None
    debounce_ms: int = 100
    thresholds: Optional[Dict[str, float]] = None
    state_map: Optional[Dict[str, str]] = None
    report_on_change_only: Optional[bool] = None
    params: Dict[str, Any] = field(default_factory=dict)

    def effective_mode(self) -> str:
        if self.mode:
            return self.mode
        if self.sensor_type in {"digital_gpio"}:
            return "digital"
        return "analog"

    def effective_report_on_change(self, runtime: RuntimeConfig) -> bool:
        if self.report_on_change_only is None:
            return runtime.report_on_change_only
        return self.report_on_change_only


@dataclass
class AppConfig:
    device: DeviceConfig
    network: NetworkConfig
    storage: StorageConfig
    runtime: RuntimeConfig
    sensors: List[SensorConfig]

    def validate(self) -> None:
        if not self.device.device_id:
            raise ValueError("device.id is required")
        if not self.network.base_url:
            raise ValueError("network.base_url is required")
        if not self.storage.queue_db_path:
            raise ValueError("storage.queue_db_path is required")
        if not self.sensors:
            raise ValueError("At least one sensor is required")


def _load_device(data: Dict[str, Any]) -> DeviceConfig:
    return DeviceConfig(
        device_id=data.get("id", ""),
        location=data.get("location"),
        firmware=data.get("firmware", "0.1.0"),
    )


def _load_network(data: Dict[str, Any]) -> NetworkConfig:
    return NetworkConfig(
        base_url=data.get("base_url", ""),
        api_token=data.get("api_token"),
        ca_cert_path=data.get("ca_cert_path"),
        batch_size=int(data.get("batch_size", 25)),
        flush_interval_seconds=int(data.get("flush_interval_seconds", 15)),
        retry_max_seconds=int(data.get("retry_max_seconds", 300)),
        connect_timeout_seconds=int(data.get("connect_timeout_seconds", 5)),
        read_timeout_seconds=int(data.get("read_timeout_seconds", 10)),
    )


def _load_storage(data: Dict[str, Any]) -> StorageConfig:
    return StorageConfig(queue_db_path=data.get("queue_db_path", "queue.db"))


def _load_runtime(data: Dict[str, Any]) -> RuntimeConfig:
    return RuntimeConfig(
        poll_interval_ms=int(data.get("poll_interval_ms", 200)),
        report_on_change_only=bool(data.get("report_on_change_only", True)),
    )


def _load_sensor(data: Dict[str, Any]) -> SensorConfig:
    known_keys = {
        "id",
        "type",
        "mode",
        "debounce_ms",
        "thresholds",
        "state_map",
        "report_on_change_only",
    }
    params = {key: value for key, value in data.items() if key not in known_keys}
    return SensorConfig(
        sensor_id=data.get("id", ""),
        sensor_type=data.get("type", ""),
        mode=data.get("mode"),
        debounce_ms=int(data.get("debounce_ms", 100)),
        thresholds=data.get("thresholds"),
        state_map=data.get("state_map"),
        report_on_change_only=data.get("report_on_change_only"),
        params=params,
    )


def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as handle:
        raw = json.load(handle)
    resolved = _resolve_obj(raw)
    config = AppConfig(
        device=_load_device(resolved.get("device", {})),
        network=_load_network(resolved.get("network", {})),
        storage=_load_storage(resolved.get("storage", {})),
        runtime=_load_runtime(resolved.get("runtime", {})),
        sensors=[_load_sensor(item) for item in resolved.get("sensors", [])],
    )
    config.validate()
    return config
