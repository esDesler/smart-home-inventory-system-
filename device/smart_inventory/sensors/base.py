from abc import ABC, abstractmethod
from typing import Optional, Tuple


class Sensor(ABC):
    def __init__(self, sensor_id: str) -> None:
        self.sensor_id = sensor_id

    @abstractmethod
    def read(self) -> Tuple[Optional[float], Optional[float]]:
        """Return raw_value, normalized_value."""
        raise NotImplementedError
