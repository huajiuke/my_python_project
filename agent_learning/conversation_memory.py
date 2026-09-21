"""SQLite-backed conversation history for multi-turn Agent sessions."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_MEMORY_DB = (
    Path(__file__).resolve().parent / "data" / "conversation_memory.db"
)
_VALID_ROLES = {"user", "assistant"}


class ConversationMemory:
    """Persist messages by session_id and return bounded recent history."""

    def __init__(
        self,
        database_path: str | Path = DEFAULT_MEMORY_DB,
        *,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        self.database_path = str(database_path)
        self._owns_connection = connection is None

        if connection is None:
            if self.database_path != ":memory:":
                Path(self.database_path).expanduser().resolve().parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )
            self._connection = sqlite3.connect(self.database_path)
        else:
            self._connection = connection

        self._connection.row_factory = sqlite3.Row
        self._initialize_schema()

    def _initialize_schema(self) -> None:
        """Create the append-only message table used by every session."""
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversation_session_id
                ON conversation_messages (session_id, id)
                """
            )

    @staticmethod
    def _normalize_session_id(session_id: str) -> str:
        normalized = session_id.strip()
        if not normalized:
            raise ValueError('session_id must not be empty')
        return normalized

    @staticmethod
    def _validate_message(role: str, content: str) -> None:
        if role not in _VALID_ROLES:
            raise ValueError(f'unsupported message role: {role}')
        if not isinstance(content, str):
            raise TypeError('message content must be a string')

    def append(self, session_id: str, role: str, content: str) -> None:
        """Append one message to a session."""
        session = self._normalize_session_id(session_id)
        self._validate_message(role, content)
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO conversation_messages (session_id, role, content)
                VALUES (?, ?, ?)
                """,
                (session, role, content),
            )

    def append_many(
        self,
        session_id: str,
        messages: list[dict[str, str]],
    ) -> None:
        """Append a complete question/answer round in one transaction."""
        session = self._normalize_session_id(session_id)
        rows: list[tuple[str, str, str]] = []
        for message in messages:
            role = message.get('role', '')
            content = message.get('content', '')
            self._validate_message(role, content)
            rows.append((session, role, content))

        if not rows:
            return
        with self._connection:
            self._connection.executemany(
                """
                INSERT INTO conversation_messages (session_id, role, content)
                VALUES (?, ?, ?)
                """,
                rows,
            )

    def recent(
        self,
        session_id: str,
        limit: int,
    ) -> list[dict[str, str]]:
        """Return the latest messages in chronological order."""
        session = self._normalize_session_id(session_id)
        if limit <= 0:
            return []

        rows = self._connection.execute(
            """
            SELECT role, content
            FROM (
                SELECT id, role, content
                FROM conversation_messages
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
            ) AS recent_messages
            ORDER BY id ASC
            """,
            (session, limit),
        ).fetchall()
        return [
            {"role": str(row['role']), "content": str(row['content'])}
            for row in rows
        ]

    def clear(self, session_id: str) -> int:
        """Delete all messages in one session and return the row count."""
        session = self._normalize_session_id(session_id)
        with self._connection:
            cursor = self._connection.execute(
                'DELETE FROM conversation_messages WHERE session_id = ?',
                (session,),
            )
        return int(cursor.rowcount)

    def close(self) -> None:
        """Close the connection only when this instance owns it."""
        if self._owns_connection:
            self._connection.close()

    def __enter__(self) -> ConversationMemory:
        return self

    def __exit__(
        self,
        exc_type: Any,
        exc_value: Any,
        traceback: Any,
    ) -> None:
        self.close()
