"""Message store for received emergency signals.

Uses SQLite when the filesystem is writable (local runs) so alerts
survive a restart; falls back to an in-memory dict when it is not
(e.g. a read-only serverless filesystem). Thread-safe.

NOTE for hosting: a serverless platform (Vercel) has an ephemeral,
often read-only filesystem, so this falls back to in-memory and data
does not persist between cold starts. For real deployment, point
DB_PATH at a writable disk or replace this with a hosted database
(Postgres / Supabase).
"""

import os
import json
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any

_COLUMNS = [
    "message_id", "source_id", "emergency_code", "severity", "timestamp",
    "origin_lat", "origin_lon", "location_source", "fallback_lat",
    "fallback_lon", "ttl", "hop_count",
]


class MessageStore:
    def __init__(self, db_path: str | None = None):
        self._lock = threading.Lock()
        self._mem: dict[str, dict[str, Any]] = {}
        self._db_path = db_path or os.environ.get("DB_PATH", "emergency.db")
        self._use_db = self._try_init_db()

    # ------------------------------------------------------------------
    def _try_init_db(self) -> bool:
        try:
            con = sqlite3.connect(self._db_path)
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    message_id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL,
                    emergency_code INTEGER,
                    severity INTEGER,
                    timestamp INTEGER,
                    origin_lat REAL,
                    origin_lon REAL,
                    location_source INTEGER,
                    fallback_lat REAL,
                    fallback_lon REAL,
                    ttl INTEGER,
                    hop_count INTEGER,
                    emergency_name TEXT,
                    location_name TEXT,
                    received_at TEXT,
                    acknowledged INTEGER DEFAULT 0,
                    acknowledged_at TEXT
                )
                """
            )
            con.commit()
            con.close()
            return True
        except Exception as exc:  # read-only FS, etc.
            print(f"[store] SQLite unavailable ({exc}); using in-memory store")
            return False

    def _conn(self):
        con = sqlite3.connect(self._db_path)
        con.row_factory = sqlite3.Row
        return con

    # ------------------------------------------------------------------
    def add(self, msg: dict[str, Any]) -> str:
        """Insert a new message. Returns 'received' or 'duplicate'."""
        with self._lock:
            mid = msg["message_id"]
            msg = dict(msg)
            msg.setdefault("received_at", datetime.now(timezone.utc).isoformat())
            msg.setdefault("acknowledged", False)

            if self._use_db:
                con = self._conn()
                exists = con.execute(
                    "SELECT 1 FROM messages WHERE message_id=?", (mid,)
                ).fetchone()
                if exists:
                    con.close()
                    return "duplicate"
                cols = _COLUMNS + ["emergency_name", "location_name",
                                   "received_at", "acknowledged"]
                vals = [msg.get(c) for c in _COLUMNS] + [
                    msg.get("emergency_name"), msg.get("location_name"),
                    msg["received_at"], 1 if msg["acknowledged"] else 0,
                ]
                con.execute(
                    f"INSERT INTO messages ({','.join(cols)}) "
                    f"VALUES ({','.join('?' for _ in cols)})",
                    vals,
                )
                con.commit()
                con.close()
                return "received"

            if mid in self._mem:
                return "duplicate"
            self._mem[mid] = msg
            return "received"

    def list(self) -> list[dict[str, Any]]:
        """All messages, newest first."""
        with self._lock:
            if self._use_db:
                con = self._conn()
                rows = con.execute(
                    "SELECT * FROM messages ORDER BY received_at DESC"
                ).fetchall()
                con.close()
                out = []
                for r in rows:
                    d = dict(r)
                    d["acknowledged"] = bool(d.get("acknowledged"))
                    out.append(d)
                return out
            return list(self._mem.values())[::-1]

    def get(self, mid: str) -> dict[str, Any] | None:
        with self._lock:
            if self._use_db:
                con = self._conn()
                r = con.execute(
                    "SELECT * FROM messages WHERE message_id=?", (mid,)
                ).fetchone()
                con.close()
                if r is None:
                    return None
                d = dict(r)
                d["acknowledged"] = bool(d.get("acknowledged"))
                return d
            return self._mem.get(mid)

    def acknowledge(self, mid: str) -> bool:
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            if self._use_db:
                con = self._conn()
                cur = con.execute(
                    "UPDATE messages SET acknowledged=1, acknowledged_at=? "
                    "WHERE message_id=?",
                    (now, mid),
                )
                con.commit()
                changed = cur.rowcount > 0
                con.close()
                return changed
            m = self._mem.get(mid)
            if not m:
                return False
            m["acknowledged"] = True
            m["acknowledged_at"] = now
            return True

    def count(self) -> int:
        with self._lock:
            if self._use_db:
                con = self._conn()
                n = con.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
                con.close()
                return n
            return len(self._mem)

    @property
    def backend(self) -> str:
        return "sqlite" if self._use_db else "in-memory"
