from typing import Optional, Tuple

from .base import Sensor


class FileSensor(Sensor):
    def __init__(
        self,
        sensor_id: str,
        path: str,
        mode: str = "analog",
        scale_factor: float = 1.0,
        tare_offset: float = 0.0,
    ) -> None:
        super().__init__(sensor_id)
        self._path = path
        self._mode = mode
        self._scale_factor = scale_factor
        self._tare_offset = tare_offset

    def read(self) -> Tuple[Optional[float], Optional[float]]:
        try:
            with open(self._path, "r", encoding="utf-8") as handle:
                content = handle.read().strip()
        except FileNotFoundError:
            return None, None

        if not content:
            return None, None

        try:
            raw = float(content)
        except ValueError:
            return None, None

        if self._mode == "digital":
            value = 1.0 if raw else 0.0
            return value, value

        normalized = (raw - self._tare_offset) / self._scale_factor
        return raw, normalized
