from typing import Any, Dict

from .base import Sensor
from .digital_gpio import DigitalGPIOSensor
from .file_sensor import FileSensor
from .hx711 import HX711Sensor


def create_sensor(sensor_type: str, sensor_id: str, params: Dict[str, Any]) -> Sensor:
    if sensor_type == "digital_gpio":
        return DigitalGPIOSensor(sensor_id=sensor_id, **params)
    if sensor_type == "file_sensor":
        return FileSensor(sensor_id=sensor_id, **params)
    if sensor_type == "hx711":
        return HX711Sensor(sensor_id=sensor_id, **params)
    raise ValueError(f"Unsupported sensor type: {sensor_type}")


__all__ = ["Sensor", "create_sensor"]
