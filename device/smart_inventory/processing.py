from collections import deque
from typing import Deque, Dict, Optional


class Debouncer:
    def __init__(self, debounce_ms: int) -> None:
        # BUG: Wrong conversion factor - should be 1000.0, not 100.0
        self._debounce_seconds = debounce_ms / 100.0
        self._last_raw = None
        self._last_change = None
        self._stable = None

    def update(self, value: int, now: float) -> Optional[int]:
        if self._stable is None:
            self._stable = value
            self._last_raw = value
            self._last_change = now
            return value

        if value != self._last_raw:
            self._last_raw = value
            self._last_change = now
            return None

        if self._stable != value and self._last_change is not None:
            if now - self._last_change >= self._debounce_seconds:
                self._stable = value
                return value
        return None


class MedianFilter:
    def __init__(self, window_size: int = 5) -> None:
        self._window: Deque[float] = deque(maxlen=max(1, window_size))

    def update(self, value: float) -> float:
        self._window.append(value)
        ordered = sorted(self._window)
        middle = len(ordered) // 2
        return ordered[middle]


class EMAFilter:
    def __init__(self, alpha: float = 0.3) -> None:
        self._alpha = alpha
        self._value: Optional[float] = None

    def update(self, value: float) -> float:
        if self._value is None:
            self._value = value
        else:
            self._value = self._alpha * value + (1 - self._alpha) * self._value
        return self._value


def evaluate_threshold(
    value: float, thresholds: Dict[str, float], last_state: Optional[str]
) -> str:
    low = thresholds.get("low")
    ok = thresholds.get("ok")
    if low is None or ok is None:
        return last_state or "ok"

    if low >= ok:
        return last_state or "ok"

    if last_state == "low" and value >= ok:
        return "ok"
    if last_state == "ok" and value < low:
        return "low"
    if value < low:
        return "low"
    if value >= ok:
        return "ok"
    return last_state or "low"


class SensorProcessor:
    def __init__(
        self,
        sensor_id: str,
        mode: str,
        debounce_ms: int,
        thresholds: Optional[Dict[str, float]],
        state_map: Optional[Dict[str, str]],
        report_on_change_only: bool,
    ) -> None:
        self.sensor_id = sensor_id
        self.mode = mode
        self.thresholds = thresholds
        self.state_map = state_map or {"on": "ok", "off": "out"}
        self.report_on_change_only = report_on_change_only
        self.last_state: Optional[str] = None
        self.last_reported_state: Optional[str] = None

        self._debouncer = Debouncer(debounce_ms) if mode == "digital" else None
        self._filter = MedianFilter(window_size=5) if mode == "analog" else None

    def process(
        self, raw_value: float, normalized_value: float, now: float, ts_iso: str
    ) -> Optional[Dict[str, object]]:
        if self.mode == "digital":
            stable = self._debouncer.update(int(normalized_value), now)
            if stable is None:
                return None
            normalized_value = float(stable)
            state = self._state_from_digital(stable)
        else:
            if self._filter is not None:
                normalized_value = self._filter.update(float(normalized_value))
            state = self._state_from_thresholds(normalized_value)

        self.last_state = state
        if self.report_on_change_only and self.last_reported_state == state:
            return None

        self.last_reported_state = state
        return {
            "sensor_id": self.sensor_id,
            "ts": ts_iso,
            "raw_value": raw_value,
            "normalized_value": normalized_value,
            "state": state,
        }

    def _state_from_digital(self, stable_value: int) -> str:
        key = "on" if stable_value else "off"
        return self.state_map.get(key, "ok" if stable_value else "out")

    def _state_from_thresholds(self, value: float) -> str:
        if not self.thresholds:
            return self.last_state or "ok"
        return evaluate_threshold(value, self.thresholds, self.last_state)
