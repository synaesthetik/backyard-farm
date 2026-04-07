"""SQLite store-and-forward buffer for sensor readings.

Every reading is stored locally before MQTT publish. On reconnect,
unsent readings are flushed in chronological order (INFRA-03).
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime


class ReadingBuffer:
    def __init__(self, db_path: str = "readings.db"):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._create_table()

    def _create_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                payload TEXT NOT NULL,
                ts TEXT NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_readings_unsent ON readings (sent, ts)"
        )
        self._conn.commit()

    def store(self, topic: str, payload: dict, ts: str) -> int:
        """Store a reading. Returns the row ID."""
        cursor = self._conn.execute(
            "INSERT INTO readings (topic, payload, ts, sent) VALUES (?, ?, ?, 0)",
            (topic, json.dumps(payload), ts)
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_unsent(self, limit: int = 100) -> list:
        """Get unsent readings ordered by timestamp ASC (chronological).
        Returns list of (id, topic, payload_json).
        """
        rows = self._conn.execute(
            "SELECT id, topic, payload FROM readings WHERE sent=0 ORDER BY ts ASC LIMIT ?",
            (limit,)
        ).fetchall()
        return rows

    def mark_sent(self, row_id: int):
        """Mark a reading as successfully published."""
        self._conn.execute("UPDATE readings SET sent=1 WHERE id=?", (row_id,))
        self._conn.commit()

    def purge_sent(self, keep_hours: int = 24):
        """Delete sent readings older than keep_hours."""
        self._conn.execute(
            "DELETE FROM readings WHERE sent=1 AND created_at < datetime('now', ?)",
            (f'-{keep_hours} hours',)
        )
        self._conn.commit()

    def close(self):
        self._conn.close()
