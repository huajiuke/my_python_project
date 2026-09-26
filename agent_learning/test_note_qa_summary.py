"""Integration tests for rolling summaries in the note QA agent."""

import sqlite3
import unittest
from pathlib import Path
from typing import Any

from agent_learning.conversation_memory import ConversationMemory
from agent_learning.note_qa_agent import NoteQAAgent
from agent_learning.note_search import NoteSearcher
from agent_learning.tool_calling_agent import MockLLM


NOTE_ROOT = Path(__file__).resolve().parent / 'fixtures' / 'note_root'


class RecordingSummarizer:
    """Record compacted windows and optionally simulate a model failure."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[tuple[str | None, list[dict[str, Any]]]] = []

    def summarize(
        self,
        previous_summary: str | None,
        messages: list[dict[str, Any]],
    ) -> str:
        self.calls.append((previous_summary, messages))
        if self.fail:
            raise RuntimeError('summary failure')
        return f'summary-{len(self.calls)}'


class NoteQAAgentSummaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.connection = sqlite3.connect(':memory:')
        self.memory = ConversationMemory(connection=self.connection)
        self.addCleanup(self.connection.close)

    def _create_agent(
        self,
        *,
        summarizer: RecordingSummarizer,
        max_history_rounds: int = 1,
        summary_trigger_rounds: int = 2,
        session_id: str = 'session-1',
        llm: MockLLM | None = None,
    ) -> NoteQAAgent:
        return NoteQAAgent(
            searcher=NoteSearcher(roots=(str(NOTE_ROOT),)),
            llm=llm or MockLLM(
                [{'type': 'final', 'content': 'model answer'}]
            ),
            memory=self.memory,
            session_id=session_id,
            max_history_rounds=max_history_rounds,
            summarizer=summarizer,
            summary_trigger_rounds=summary_trigger_rounds,
        )

    def test_below_threshold_does_not_summarize(self) -> None:
        summarizer = RecordingSummarizer()
        agent = self._create_agent(
            summarizer=summarizer,
            summary_trigger_rounds=3,
        )

        agent.ask('session first question')
        agent.ask('session second question')

        self.assertEqual(summarizer.calls, [])
        self.assertIsNone(self.memory.latest_summary('session-1'))

    def test_threshold_compacts_only_old_complete_rounds(self) -> None:
        summarizer = RecordingSummarizer()
        agent = self._create_agent(summarizer=summarizer)

        agent.ask('session first question')
        agent.ask('session second question')

        self.assertEqual(len(summarizer.calls), 1)
        previous_summary, compacted = summarizer.calls[0]
        self.assertIsNone(previous_summary)
        self.assertEqual(
            [message['content'] for message in compacted],
            ['session first question', 'model answer'],
        )
        stored = self.memory.latest_summary('session-1')
        self.assertIsNotNone(stored)
        self.assertEqual(stored['summary'], 'summary-1')
        self.assertEqual(stored['summarized_through_id'], compacted[-1]['id'])
        self.assertEqual(
            [message['content'] for message in agent._unsummarized_history],
            ['session second question', 'model answer'],
        )
        self.assertEqual(
            len(self.memory.recent('session-1', limit=10)),
            4,
        )

    def test_restart_uses_summary_and_recent_raw_history(self) -> None:
        first_summarizer = RecordingSummarizer()
        first_agent = self._create_agent(summarizer=first_summarizer)
        first_agent.ask('session first question')
        first_agent.ask('session second question')

        second_llm = MockLLM(
            [{'type': 'final', 'content': 'second agent answer'}]
        )
        second_summarizer = RecordingSummarizer()
        second_agent = self._create_agent(
            summarizer=second_summarizer,
            llm=second_llm,
        )
        second_agent.ask('session third question')

        request = second_llm.seen_messages[0]
        system_messages = [
            str(message['content'])
            for message in request
            if message['role'] == 'system'
        ]
        history_messages = [
            str(message['content'])
            for message in request
            if message['role'] in {'user', 'assistant'}
        ]
        self.assertTrue(
            any('summary-1' in content for content in system_messages)
        )
        self.assertIn('session second question', history_messages)
        self.assertIn('model answer', history_messages)
        self.assertNotIn('session first question', history_messages)

    def test_summary_failure_keeps_messages_and_pointer(self) -> None:
        summarizer = RecordingSummarizer(fail=True)
        agent = self._create_agent(summarizer=summarizer)

        answer = agent.ask('session first question')
        agent.ask('session second question')

        self.assertIn('model answer', answer)
        self.assertIsNone(self.memory.latest_summary('session-1'))
        self.assertEqual(agent._summary_pointer, 0)
        self.assertEqual(
            len(self.memory.recent('session-1', limit=10)),
            4,
        )
        self.assertEqual(len(agent._unsummarized_history), 4)

    def test_sessions_have_independent_summaries(self) -> None:
        summarizer = RecordingSummarizer()
        first_agent = self._create_agent(
            summarizer=summarizer,
            session_id='session-a',
        )
        second_agent = self._create_agent(
            summarizer=summarizer,
            session_id='session-b',
        )

        first_agent.ask('session alpha')
        first_agent.ask('session alpha followup')
        second_agent.ask('session beta')
        second_agent.ask('session beta followup')

        first_summary = self.memory.latest_summary('session-a')
        second_summary = self.memory.latest_summary('session-b')
        self.assertEqual(first_summary['summary'], 'summary-1')
        self.assertEqual(second_summary['summary'], 'summary-2')
        self.assertEqual(first_agent._summary, 'summary-1')
        self.assertEqual(second_agent._summary, 'summary-2')

    def test_answer_remains_stateless_with_summary_enabled(self) -> None:
        summarizer = RecordingSummarizer()
        agent = self._create_agent(summarizer=summarizer)

        agent.answer('session question')

        self.assertEqual(summarizer.calls, [])
        self.assertEqual(self.memory.recent('session-1', limit=10), [])
        self.assertIsNone(self.memory.latest_summary('session-1'))


if __name__ == '__main__':
    unittest.main()
