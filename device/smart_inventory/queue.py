import os
import sqlite3
from typing import Dict, List, Optional


class ReadingQueue:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._ensure_directory()
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _ensure_directory(self) -> None:
        directory = os.path.dirname(self._db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def _init_schema(self) -> None:
        cursor = self._conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS readings (
                seq_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sensor_id TEXT NOT NULL,
                ts TEXT NOT NULL,
                raw_value REAL,
                normalized_value REAL,
                state TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def enqueue(self, reading: Dict[str, object]) -> int:
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO readings (sensor_id, ts, raw_value, normalized_value, state)
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                reading["sensor_id"],
                reading["ts"],
                reading.get("raw_value"),
                reading.get("normalized_value"),
                reading["state"],
            ),
        )
        self._conn.commit()
        return int(cursor.lastrowid)

    def get_batch(self, limit: int) -> List[Dict[str, object]]:
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT seq_id, sensor_id, ts, raw_value, normalized_value, state
            FROM readings
            ORDER BY seq_id ASC
            LIMIT ?;
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def ack_upto(self, seq_id: int) -> None:
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM readings WHERE seq_id <= ?;", (seq_id,))
        self._conn.commit()

    def pending_count(self) -> int:
        cursor = self._conn.cursor()
        cursor.execute("SELECT COUNT(*) AS count FROM readings;")
        row = cursor.fetchone()
        return int(row["count"])

    def max_seq_id(self) -> Optional[int]:
        cursor = self._conn.cursor()
        cursor.execute("SELECT MAX(seq_id) AS max_id FROM readings;")
        row = cursor.fetchone()
        if row and row["max_id"] is not None:
            return int(row["max_id"])
        return None
