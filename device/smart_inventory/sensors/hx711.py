from typing import Optional, Tuple

from .base import Sensor

try:
    from hx711 import HX711
except ImportError:  # pragma: no cover - optional dependency
    HX711 = None


class HX711Sensor(Sensor):
    def __init__(
        self,
        sensor_id: str,
        gpio_dout: int,
        gpio_sck: int,
        scale_factor: float = 1.0,
        tare_offset: float = 0.0,
        readings: int = 5,
        gain: Optional[int] = None,
    ) -> None:
        super().__init__(sensor_id)
        if HX711 is None:
            raise RuntimeError("hx711 library is required for HX711 sensors")
        self._hx711 = HX711(gpio_dout, gpio_sck)
        if gain is not None and hasattr(self._hx711, "set_gain"):
            self._hx711.set_gain(gain)
        self._scale_factor = scale_factor if scale_factor else 1.0
        self._tare_offset = tare_offset
        self._readings = readings

    def read(self) -> Tuple[Optional[float], Optional[float]]:
        raw = self._read_raw()
        if raw is None:
            return None, None
        normalized = (raw - self._tare_offset) / self._scale_factor
        return float(raw), float(normalized)

    def _read_raw(self) -> Optional[float]:
        if hasattr(self._hx711, "get_raw_data_mean"):
            raw = self._hx711.get_raw_data_mean(readings=self._readings)
            return float(raw) if raw is not None else None
        if hasattr(self._hx711, "read"):
            raw = self._hx711.read()
            return float(raw) if raw is not None else None
        if hasattr(self._hx711, "get_reading"):
            raw = self._hx711.get_reading()
            return float(raw) if raw is not None else None
        return None
