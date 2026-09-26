"""Tests for LLM-backed rolling conversation summaries."""

import unittest
from typing import Any

from agent_learning.conversation_summarizer import ConversationSummarizer


class RecordingSummaryLLM:
    """Return one configured response and retain the summarizer prompt."""

    def __init__(self, content: str = 'merged summary') -> None:
        self.content = content
        self.calls: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []

    def decide(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self.calls.append((messages, tools))
        return {'role': 'assistant', 'content': self.content}


class ConversationSummarizerTest(unittest.TestCase):
    def test_merges_previous_summary_and_new_messages(self) -> None:
        llm = RecordingSummaryLLM('merged')
        summarizer = ConversationSummarizer(llm)

        summary = summarizer.summarize(
            'previous facts',
            [
                {'role': 'user', 'content': 'new question'},
                {'role': 'assistant', 'content': 'new answer'},
            ],
        )

        self.assertEqual(summary, 'merged')
        messages, tools = llm.calls[0]
        self.assertEqual(tools, [])
        self.assertIn('previous facts', messages[1]['content'])
        self.assertIn('user: new question', messages[1]['content'])
        self.assertIn('assistant: new answer', messages[1]['content'])

    def test_rejects_empty_messages_and_empty_model_response(self) -> None:
        with self.assertRaises(ValueError):
            ConversationSummarizer(RecordingSummaryLLM()).summarize(
                None,
                [],
            )

        with self.assertRaises(RuntimeError):
            ConversationSummarizer(RecordingSummaryLLM('   ')).summarize(
                None,
                [{'role': 'user', 'content': 'question'}],
            )

    def test_summary_is_bounded_by_max_chars(self) -> None:
        summarizer = ConversationSummarizer(
            RecordingSummaryLLM('x' * 100),
            max_summary_chars=20,
        )

        summary = summarizer.summarize(
            None,
            [{'role': 'user', 'content': 'question'}],
        )

        self.assertLessEqual(len(summary), 20)
        self.assertTrue(summary.endswith('...[摘要已截断]'))

    def test_invalid_max_chars_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ConversationSummarizer(
                RecordingSummaryLLM(),
                max_summary_chars=0,
            )


if __name__ == '__main__':
    unittest.main()
