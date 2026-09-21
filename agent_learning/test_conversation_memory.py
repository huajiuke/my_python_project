"""Tests for SQLite-backed conversation memory."""

import sqlite3
import unittest

from agent_learning.conversation_memory import ConversationMemory


class ConversationMemoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(':memory:')
        self.memory = ConversationMemory(connection=self.connection)

    def tearDown(self) -> None:
        self.connection.close()

    def test_recent_returns_latest_messages_in_order(self) -> None:
        self.memory.append_many(
            'session-1',
            [
                {'role': 'user', 'content': 'question-1'},
                {'role': 'assistant', 'content': 'answer-1'},
            ],
        )
        self.memory.append_many(
            'session-1',
            [
                {'role': 'user', 'content': 'question-2'},
                {'role': 'assistant', 'content': 'answer-2'},
            ],
        )

        messages = self.memory.recent('session-1', limit=3)

        self.assertEqual(
            [message['content'] for message in messages],
            ['answer-1', 'question-2', 'answer-2'],
        )

    def test_sessions_are_isolated(self) -> None:
        self.memory.append('session-a', 'user', 'alpha')
        self.memory.append('session-b', 'user', 'beta')

        self.assertEqual(
            self.memory.recent('session-a', limit=10),
            [{'role': 'user', 'content': 'alpha'}],
        )
        self.assertEqual(
            self.memory.recent('session-b', limit=10),
            [{'role': 'user', 'content': 'beta'}],
        )

    def test_clear_removes_only_selected_session(self) -> None:
        self.memory.append('session-a', 'user', 'alpha')
        self.memory.append('session-b', 'user', 'beta')

        deleted = self.memory.clear('session-a')

        self.assertEqual(deleted, 1)
        self.assertEqual(self.memory.recent('session-a', limit=10), [])
        self.assertEqual(len(self.memory.recent('session-b', limit=10)), 1)

    def test_new_connection_reads_persisted_messages(self) -> None:
        database_uri = (
            'file:conversation_memory_test?mode=memory&cache=shared'
        )
        anchor = sqlite3.connect(database_uri, uri=True)
        reopened_connection = sqlite3.connect(database_uri, uri=True)
        self.addCleanup(anchor.close)
        self.addCleanup(reopened_connection.close)
        first = ConversationMemory(connection=anchor)
        first.append('session-1', 'user', 'persisted')

        reopened = ConversationMemory(connection=reopened_connection)

        self.assertEqual(
            reopened.recent('session-1', limit=10),
            [{'role': 'user', 'content': 'persisted'}],
        )

    def test_invalid_session_and_role_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.memory.recent('   ', limit=10)
        with self.assertRaises(ValueError):
            self.memory.append('session-1', 'system', 'hidden')


if __name__ == '__main__':
    unittest.main()
