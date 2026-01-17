from typing import Dict, Optional


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


def resolve_state(
    normalized_value: Optional[float],
    reading_state: str,
    last_state: Optional[str],
    thresholds: Optional[Dict[str, float]],
    state_map: Optional[Dict[str, str]],
) -> str:
    if thresholds and normalized_value is not None:
        return evaluate_threshold(normalized_value, thresholds, last_state)
    if state_map and normalized_value is not None:
        key = "on" if normalized_value else "off"
        return state_map.get(key, reading_state)
    return reading_state
