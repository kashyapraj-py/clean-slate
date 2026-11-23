"""Durable SQLite cleanup journal. No database stores file contents."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .models import CleanSlateError


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Journal:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir.expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.database_path = self.data_dir / "history.sqlite3"
        with self.connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS operations (
                    id TEXT PRIMARY KEY,
                    root TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('running','completed','partial','failed'))
                );
                CREATE TABLE IF NOT EXISTS items (
                    id TEXT NOT NULL,
                    operation_id TEXT NOT NULL REFERENCES operations(id),
                    original_path TEXT NOT NULL,
                    quarantine_path TEXT NOT NULL,
                    category TEXT NOT NULL,
                    bytes INTEGER NOT NULL,
                    restored_at TEXT,
                    PRIMARY KEY (operation_id, id)
                );
                CREATE INDEX IF NOT EXISTS ix_items_operation ON items(operation_id);
            """)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=20)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=20000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def start(self, operation_id: str, root: str) -> None:
        with self.connection() as conn:
            conn.execute("INSERT INTO operations VALUES (?, ?, ?, ?)",
                         (operation_id, root, utc_now(), "running"))

    def record_item(
        self, operation_id: str, item_id: str, original: Path,
        quarantine: Path, category: str, bytes_: int,
    ) -> None:
        with self.connection() as conn:
            conn.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?, ?, NULL)",
                         (item_id, operation_id, str(original), str(quarantine), category, bytes_))

    def finish(self, operation_id: str, status: str) -> None:
        if status not in {"completed", "partial", "failed"}:
            raise ValueError("Invalid operation status")
        with self.connection() as conn:
            conn.execute("UPDATE operations SET status=? WHERE id=?", (status, operation_id))

    def mark_restored(self, operation_id: str, item_id: str) -> None:
        with self.connection() as conn:
            conn.execute(
                "UPDATE items SET restored_at=? WHERE operation_id=? AND id=? AND restored_at IS NULL",
                (utc_now(), operation_id, item_id),
            )
            if conn.total_changes == 0:
                raise CleanSlateError("This item has already been restored.")

    def operation(self, operation_id: str) -> dict:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM operations WHERE id=?", (operation_id,)).fetchone()
            if row is None:
                raise CleanSlateError(f"Unknown cleanup operation: {operation_id}")
            return self._to_dict(conn, row)

    def history(self, limit: int = 30) -> list[dict]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM operations ORDER BY created_at DESC, id DESC LIMIT ?",
                (min(max(1, limit), 200),),
            ).fetchall()
            return [self._to_dict(conn, row) for row in rows]

    @staticmethod
    def _to_dict(conn: sqlite3.Connection, operation: sqlite3.Row) -> dict:
        items = [dict(item) for item in conn.execute(
            "SELECT * FROM items WHERE operation_id=? ORDER BY original_path", (operation["id"],)
        ).fetchall()]
        return {
            **dict(operation), "items": items,
            "bytes": sum(item["bytes"] for item in items),
            "restored_count": sum(item["restored_at"] is not None for item in items),
        }
