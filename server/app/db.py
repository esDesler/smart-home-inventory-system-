import json
import os
import sqlite3
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional

from .config import AppConfig


def _ensure_directory(db_path: str) -> None:
    directory = os.path.dirname(db_path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_db(config: AppConfig) -> Iterator[sqlite3.Connection]:
    _ensure_directory(config.db_path)
    conn = _connect(config.db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(config: AppConfig) -> None:
    with get_db(config) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                name TEXT,
                location TEXT,
                firmware TEXT,
                last_seen TEXT
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sensors (
                id TEXT PRIMARY KEY,
                device_id TEXT,
                type TEXT,
                thresholds TEXT,
                state_map TEXT,
                last_state TEXT,
                last_value REAL,
                last_update TEXT,
                FOREIGN KEY(device_id) REFERENCES devices(id)
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id TEXT PRIMARY KEY,
                sensor_id TEXT,
                name TEXT NOT NULL,
                thresholds TEXT,
                unit TEXT,
                image_url TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY(sensor_id) REFERENCES sensors(id)
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                seq_id INTEGER,
                sensor_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                raw_value REAL,
                normalized_value REAL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(sensor_id, seq_id),
                FOREIGN KEY(sensor_id) REFERENCES sensors(id)
            );
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id TEXT,
                sensor_id TEXT NOT NULL,
                type TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                FOREIGN KEY(item_id) REFERENCES items(id),
                FOREIGN KEY(sensor_id) REFERENCES sensors(id)
            );
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_readings_sensor_ts ON readings(sensor_id, ts);"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);"
        )


def dumps_json(value: Optional[Dict[str, Any]]) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=True)


def loads_json(value: Optional[str]) -> Optional[Dict[str, Any]]:
    if not value:
        return None
    return json.loads(value)
