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
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    session_id TEXT PRIMARY KEY,
                    summary TEXT NOT NULL,
                    summarized_through_id INTEGER NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
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

    def messages_after(
        self,
        session_id: str,
        message_id: int,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return messages with ids greater than the summary pointer."""
        session = self._normalize_session_id(session_id)
        if message_id < 0:
            raise ValueError('message_id must not be negative')
        if limit is not None and limit <= 0:
            return []

        effective_limit = -1 if limit is None else limit
        rows = self._connection.execute(
            """
            SELECT id, role, content
            FROM conversation_messages
            WHERE session_id = ? AND id > ?
            ORDER BY id ASC
            LIMIT ?
            """,
            (session, message_id, effective_limit),
        ).fetchall()
        return [
            {
                'id': int(row['id']),
                'role': str(row['role']),
                'content': str(row['content']),
            }
            for row in rows
        ]

    def latest_summary(self, session_id: str) -> dict[str, Any] | None:
        """Return the rolling summary and the last covered message id."""
        session = self._normalize_session_id(session_id)
        row = self._connection.execute(
            """
            SELECT summary, summarized_through_id, updated_at
            FROM conversation_summaries
            WHERE session_id = ?
            """,
            (session,),
        ).fetchone()
        if row is None:
            return None
        return {
            'summary': str(row['summary']),
            'summarized_through_id': int(row['summarized_through_id']),
            'updated_at': str(row['updated_at']),
        }

    def save_summary(
        self,
        session_id: str,
        summary: str,
        summarized_through_id: int,
    ) -> None:
        """Create or replace one session's rolling summary."""
        session = self._normalize_session_id(session_id)
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError('summary must not be empty')
        if summarized_through_id <= 0:
            raise ValueError('summarized_through_id must be positive')

        exists = self._connection.execute(
            """
            SELECT 1
            FROM conversation_messages
            WHERE session_id = ? AND id = ?
            """,
            (session, summarized_through_id),
        ).fetchone()
        if exists is None:
            raise ValueError('summary pointer does not belong to this session')

        with self._connection:
            self._connection.execute(
                """
                INSERT INTO conversation_summaries (
                    session_id,
                    summary,
                    summarized_through_id
                )
                VALUES (?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    summary = excluded.summary,
                    summarized_through_id = excluded.summarized_through_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (session, summary.strip(), summarized_through_id),
            )

    def clear(self, session_id: str) -> int:
        """Delete all messages in one session and return the row count."""
        session = self._normalize_session_id(session_id)
        with self._connection:
            self._connection.execute(
                'DELETE FROM conversation_summaries WHERE session_id = ?',
                (session,),
            )
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
