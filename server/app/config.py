import os
from dataclasses import dataclass
from typing import List, Optional


def _parse_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class AppConfig:
    db_path: str
    device_tokens: List[str]
    ui_token: Optional[str]
    allow_unauth: bool
    event_queue_size: int
    event_retention_seconds: int
    event_max_rows: int
    event_replay_limit: int
    history_limit: int
    cors_origins: List[str]


def load_config() -> AppConfig:
    return AppConfig(
        db_path=os.getenv("INVENTORY_DB_PATH", "./data/inventory.db"),
        device_tokens=_parse_list(os.getenv("INVENTORY_DEVICE_TOKENS")),
        ui_token=os.getenv("INVENTORY_UI_TOKEN"),
        allow_unauth=_parse_bool(os.getenv("INVENTORY_ALLOW_UNAUTH"), default=False),
        event_queue_size=int(os.getenv("INVENTORY_EVENT_QUEUE_SIZE", "100")),
        event_retention_seconds=int(
            os.getenv("INVENTORY_EVENT_RETENTION_SECONDS", "604800")
        ),
        event_max_rows=int(os.getenv("INVENTORY_EVENT_MAX_ROWS", "10000")),
        event_replay_limit=int(os.getenv("INVENTORY_EVENT_REPLAY_LIMIT", "500")),
        history_limit=int(os.getenv("INVENTORY_HISTORY_LIMIT", "2000")),
        cors_origins=_parse_list(os.getenv("INVENTORY_CORS_ORIGINS")),
    )
