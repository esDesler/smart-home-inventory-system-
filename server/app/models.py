from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class ReadingIn(BaseModel):
    seq_id: int = Field(..., ge=0)
    sensor_id: str
    ts: str
    raw_value: Optional[float] = None
    normalized_value: Optional[float] = None
    state: str


class ReadingsBatchIn(BaseModel):
    device_id: str
    firmware: Optional[str] = None
    sent_at: Optional[str] = None
    readings: List[ReadingIn]


class ThresholdsIn(BaseModel):
    low: Optional[float] = None
    ok: Optional[float] = None


class ItemCreate(BaseModel):
    name: str
    sensor_id: Optional[str] = None
    thresholds: Optional[Dict[str, float]] = None
    unit: Optional[str] = None
    image_url: Optional[str] = None


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    sensor_id: Optional[str] = None
    thresholds: Optional[Dict[str, float]] = None
    unit: Optional[str] = None
    image_url: Optional[str] = None
