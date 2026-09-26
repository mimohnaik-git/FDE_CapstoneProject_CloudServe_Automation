"""Persistent decision log (A8). SQLite, append-only, one row per decision.
If the DB write fails, the decision is written to a JSONL fallback and the
ticket is forced to ESCALATE — an unlogged decision is never released."""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


class AuditError(RuntimeError):
    pass


_SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT, ticket_id TEXT NOT NULL, route TEXT NOT NULL,
    reasons TEXT NOT NULL, payload TEXT NOT NULL,
    config_fingerprint TEXT, created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_decisions_ticket ON decisions(ticket_id);
CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL, reviewer TEXT NOT NULL, action TEXT NOT NULL,
    note TEXT, created_at TEXT NOT NULL
);
"""


class AuditStore:
    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.executescript(_SCHEMA)
        self.fallback = Path(path + ".fallback.jsonl") if path != ":memory:" else None

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def log_decision(self, decision: dict, run_id: str | None = None) -> None:
        row = (run_id, decision["ticket_id"], decision["route"],
               json.dumps(decision["reasons"]), json.dumps(decision, default=str),
               decision.get("config_fingerprint"), self._now())
        try:
            with self._lock, self._conn:
                self._conn.execute(
                    "INSERT INTO decisions (run_id,ticket_id,route,reasons,payload,"
                    "config_fingerprint,created_at) VALUES (?,?,?,?,?,?,?)", row)
        except sqlite3.Error as e:
            raise AuditError(str(e)) from e

    def write_fallback(self, decision: dict) -> None:
        if self.fallback:
            with open(self.fallback, "a", encoding="utf-8") as f:
                f.write(json.dumps(decision, default=str) + "\n")

    def latest(self, ticket_id: str) -> dict | None:
        cur = self._conn.execute(
            "SELECT payload FROM decisions WHERE ticket_id=? ORDER BY id DESC LIMIT 1",
            (ticket_id,))
        r = cur.fetchone()
        return json.loads(r[0]) if r else None

    def count(self, run_id: str | None = None) -> int:
        if run_id:
            return self._conn.execute(
                "SELECT COUNT(*) FROM decisions WHERE run_id=?", (run_id,)).fetchone()[0]
        return self._conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]

    def record_review(self, ticket_id: str, reviewer: str, action: str, note: str = "") -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO approvals (ticket_id,reviewer,action,note,created_at) "
                "VALUES (?,?,?,?,?)", (ticket_id, reviewer, action, note, self._now()))

    def reviews(self, ticket_id: str) -> list[dict]:
        cur = self._conn.execute(
            "SELECT reviewer,action,note,created_at FROM approvals WHERE ticket_id=? "
            "ORDER BY id", (ticket_id,))
        return [dict(zip(("reviewer", "action", "note", "created_at"), r)) for r in cur]
