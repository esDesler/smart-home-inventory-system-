import datetime as dt
import os
import sqlite3
import threading
from typing import Dict, List, Optional


class ReadingQueue:
    def __init__(
        self,
        db_path: str,
        max_rows: Optional[int] = None,
        max_age_seconds: Optional[int] = None,
    ) -> None:
        self._db_path = db_path
        self._max_rows = max_rows if max_rows and max_rows > 0 else None
        self._max_age_seconds = (
            max_age_seconds if max_age_seconds and max_age_seconds > 0 else None
        )
        self._lock = threading.RLock()
        self._ensure_directory()
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _ensure_directory(self) -> None:
        directory = os.path.dirname(self._db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def _init_schema(self) -> None:
        with self._lock:
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
        with self._lock:
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
            seq_id = int(cursor.lastrowid)
        self.trim()
        return seq_id

    def get_batch(self, limit: int) -> List[Dict[str, object]]:
        with self._lock:
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
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("DELETE FROM readings WHERE seq_id <= ?;", (seq_id,))
            self._conn.commit()

    def pending_count(self) -> int:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT COUNT(*) AS count FROM readings;")
            row = cursor.fetchone()
            return int(row["count"])

    def max_seq_id(self) -> Optional[int]:
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute("SELECT MAX(seq_id) AS max_id FROM readings;")
            row = cursor.fetchone()
            if row and row["max_id"] is not None:
                return int(row["max_id"])
            return None

    def trim(self) -> None:
        if not self._max_rows and not self._max_age_seconds:
            return
        with self._lock:
            if self._max_age_seconds:
                cutoff = (
                    dt.datetime.now(dt.timezone.utc)
                    - dt.timedelta(seconds=self._max_age_seconds)
                ).isoformat()
                self._conn.execute("DELETE FROM readings WHERE ts < ?;", (cutoff,))
            if self._max_rows:
                row = self._conn.execute(
                    "SELECT COUNT(*) AS count FROM readings;"
                ).fetchone()
                count = int(row["count"]) if row else 0
                if count > self._max_rows:
                    excess = count - self._max_rows
                    self._conn.execute(
                        """
                        DELETE FROM readings
                        WHERE seq_id IN (
                            SELECT seq_id FROM readings
                            ORDER BY seq_id ASC
                            LIMIT ?
                        );
                        """,
                        (excess,),
                    )
            self._conn.commit()
