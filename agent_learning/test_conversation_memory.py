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
        message = self.memory.messages_after('session-a', 0)[0]
        self.memory.save_summary('session-a', 'alpha summary', message['id'])

        deleted = self.memory.clear('session-a')

        self.assertEqual(deleted, 1)
        self.assertEqual(self.memory.recent('session-a', limit=10), [])
        self.assertIsNone(self.memory.latest_summary('session-a'))
        self.assertEqual(len(self.memory.recent('session-b', limit=10)), 1)

    def test_messages_after_returns_incremental_window(self) -> None:
        self.memory.append_many(
            'session-1',
            [
                {'role': 'user', 'content': 'question-1'},
                {'role': 'assistant', 'content': 'answer-1'},
                {'role': 'user', 'content': 'question-2'},
                {'role': 'assistant', 'content': 'answer-2'},
            ],
        )
        messages = self.memory.messages_after('session-1', 0)

        after_first = self.memory.messages_after(
            'session-1',
            messages[0]['id'],
        )
        limited = self.memory.messages_after('session-1', 0, limit=1)

        self.assertEqual(
            [message['content'] for message in after_first],
            ['answer-1', 'question-2', 'answer-2'],
        )
        self.assertEqual(len(limited), 1)
        self.assertEqual(limited[0]['content'], 'question-1')

    def test_rolling_summary_can_be_saved_and_replaced(self) -> None:
        self.memory.append_many(
            'session-1',
            [
                {'role': 'user', 'content': 'question-1'},
                {'role': 'assistant', 'content': 'answer-1'},
            ],
        )
        message = self.memory.messages_after('session-1', 0)[-1]

        self.memory.save_summary(
            'session-1',
            'first summary',
            message['id'],
        )
        self.memory.save_summary(
            'session-1',
            'updated summary',
            message['id'],
        )

        summary = self.memory.latest_summary('session-1')
        self.assertIsNotNone(summary)
        self.assertEqual(summary['summary'], 'updated summary')
        self.assertEqual(summary['summarized_through_id'], message['id'])

    def test_summary_pointer_must_belong_to_session(self) -> None:
        self.memory.append('session-1', 'user', 'alpha')

        with self.assertRaises(ValueError):
            self.memory.save_summary('session-1', 'summary', 999)

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
        message = first.messages_after('session-1', 0)[0]
        first.save_summary('session-1', 'persisted summary', message['id'])

        reopened = ConversationMemory(connection=reopened_connection)

        self.assertEqual(
            reopened.recent('session-1', limit=10),
            [{'role': 'user', 'content': 'persisted'}],
        )
        self.assertEqual(
            reopened.latest_summary('session-1')['summary'],
            'persisted summary',
        )

    def test_invalid_session_and_role_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.memory.recent('   ', limit=10)
        with self.assertRaises(ValueError):
            self.memory.append('session-1', 'system', 'hidden')


if __name__ == '__main__':
    unittest.main()
