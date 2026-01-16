from typing import Optional, Tuple

from .base import Sensor

try:
    import RPi.GPIO as GPIO
except ImportError:  # pragma: no cover - only used on Raspberry Pi
    GPIO = None


_GPIO_READY = False


def _setup_gpio() -> None:
    global _GPIO_READY
    if _GPIO_READY:
        return
    if GPIO is None:
        raise RuntimeError("RPi.GPIO is required for digital_gpio sensors")
    GPIO.setmode(GPIO.BCM)
    _GPIO_READY = True


class DigitalGPIOSensor(Sensor):
    def __init__(
        self,
        sensor_id: str,
        gpio_pin: int,
        active_high: bool = True,
        pull: str = "up",
    ) -> None:
        super().__init__(sensor_id)
        _setup_gpio()
        self._pin = gpio_pin
        self._active_high = active_high
        pull_map = {
            "up": GPIO.PUD_UP,
            "down": GPIO.PUD_DOWN,
            "none": GPIO.PUD_OFF,
        }
        GPIO.setup(self._pin, GPIO.IN, pull_up_down=pull_map.get(pull, GPIO.PUD_UP))

    def read(self) -> Tuple[Optional[float], Optional[float]]:
        raw = GPIO.input(self._pin)
        value = 1 if raw else 0
        if not self._active_high:
            value = 0 if value else 1
        return float(value), float(value)
