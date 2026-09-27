"""四个主题接入 NoteQAAgent 之后的集成测试。"""

import json
import unittest
from pathlib import Path

from pydantic import ValidationError

from agent_learning.note_qa_agent import (
    NO_MATCH_MESSAGE,
    NoteAnswer,
    NoteChunk,
    NoteQAAgent,
)
from agent_learning.retrieval import NoteIndex
from agent_learning.tool_calling_agent import MockLLM


NOTE_ROOT = Path(__file__).resolve().parent / "fixtures" / "note_root"

# 人造长笔记：每一行都含"内容"，保证检索一次命中多块。
LONG_NOTE = "# 长文\n\n" + "\n".join(
    "第 {} 行内容，用来把片段撑大一点。".format(index)
    for index in range(1, 61)
)

# 两节内容都含"裁剪"，用来验证引用编号能区分片段。
TWO_SECTIONS = "\n".join(
    [
        "# 甲",
        "",
        "分层裁剪说明。",
        "",
        "# 乙",
        "",
        "预算与裁剪。",
    ]
)


class AgentIndexIntegrationTest(unittest.TestCase):
    def _index(self) -> NoteIndex:
        index = NoteIndex()
        self.addCleanup(index.close)
        return index

    def test_searches_via_fts5_index_and_cites_line_numbers(self) -> None:
        index = self._index()
        index.index_root(NOTE_ROOT)
        agent = NoteQAAgent(
            llm=MockLLM([{"type": "final", "content": "Session 是会话对象。"}]),
            index=index,
        )

        result = agent.answer("Session")

        self.assertIn("Session 是会话对象。", result)
        self.assertIn("sqlalchemy.md:1", result)
        self.assertEqual(len(agent.last_chunks), 1)
        self.assertIsNotNone(agent.last_budget_report)

    def test_creates_searcher_when_no_backend_given(self) -> None:
        agent = NoteQAAgent(llm=MockLLM([{"type": "final", "content": "x"}]))

        self.assertIsNotNone(agent.searcher)

    def test_blank_question_returns_no_match(self) -> None:
        index = self._index()
        index.index_root(NOTE_ROOT)
        agent = NoteQAAgent(
            llm=MockLLM([{"type": "final", "content": "不该被调用"}]),
            index=index,
        )

        self.assertEqual(agent.answer("   "), NO_MATCH_MESSAGE)
        self.assertEqual(agent.ask(""), NO_MATCH_MESSAGE)


class ContextBudgetIntegrationTest(unittest.TestCase):
    def _long_note_agent(self, **kwargs: object) -> NoteQAAgent:
        index = NoteIndex()
        self.addCleanup(index.close)
        index.index_text(LONG_NOTE, "long.md")
        return NoteQAAgent(
            llm=MockLLM([{"type": "final", "content": "答案"}]),
            index=index,
            **kwargs,
        )

    def test_notes_are_trimmed_when_budget_is_tight(self) -> None:
        agent = self._long_note_agent(
            context_budget_tokens=700,
            reserve_output_tokens=100,
        )

        agent.answer("内容")

        report = agent.last_budget_report
        self.assertIsNotNone(report)
        layers = {layer.name: layer for layer in report.layers}
        self.assertTrue(report.trimmed)
        # 系统提示是 mandatory，永远保留。
        self.assertEqual(layers["instructions"].kept_segments, 1)
        self.assertGreater(layers["notes"].kept_segments, 0)
        self.assertLess(
            layers["notes"].kept_segments,
            layers["notes"].requested_segments,
        )

    def _short_note_agent(self) -> NoteQAAgent:
        index = NoteIndex()
        self.addCleanup(index.close)
        index.index_text("# 笔记\n\n裁剪说明很短。", "note.md")
        return NoteQAAgent(
            llm=MockLLM([{"type": "final", "content": "答案"}]),
            index=index,
            context_budget_tokens=600,
            reserve_output_tokens=100,
        )

    def test_history_layer_keeps_the_latest_messages(self) -> None:
        agent = self._short_note_agent()
        history = [
            {
                "role": "user" if index % 2 == 0 else "assistant",
                "content": "第 {} 轮的历史".format(index) + "很长的填充内容" * 20,
            }
            for index in range(10)
        ]

        messages = agent._assemble_messages(
            "裁剪",
            agent._search("裁剪"),
            history,
            None,
        )

        body = [
            message for message in messages if message["role"] != "system"
        ]
        self.assertLess(len(body), len(history) + 1)
        # 丢的是最早的那几条，保留的必须是最近的。
        self.assertTrue(str(body[-2]["content"]).startswith("第 9 轮"))

        # 检索片段优先级高于历史：历史被丢，片段必须留下来。
        report = agent.last_budget_report
        self.assertIsNotNone(report)
        layers = {layer.name: layer for layer in report.layers}
        self.assertEqual(
            layers["notes"].kept_segments,
            layers["notes"].requested_segments,
        )
        self.assertTrue(layers["history"].trimmed)
        self.assertIn("裁剪", str(body[-1]["content"]))

    def test_summary_is_included_when_budget_allows(self) -> None:
        agent = self._long_note_agent()

        messages = agent._assemble_messages(
            "内容",
            agent._search("内容"),
            [],
            "之前聊过 Session 管理。",
        )

        system_text = "\n".join(
            str(message["content"])
            for message in messages
            if message["role"] == "system"
        )
        self.assertIn("之前聊过 Session 管理。", system_text)

class StructuredAnswerIntegrationTest(unittest.TestCase):
    def _agent(self, script: list[dict[str, object]]) -> NoteQAAgent:
        index = NoteIndex()
        self.addCleanup(index.close)
        index.index_text(TWO_SECTIONS, "two.md")
        return NoteQAAgent(
            llm=MockLLM(script),
            index=index,
            structured_answers=True,
        )

    def test_citations_limit_the_source_footer(self) -> None:
        agent = self._agent(
            [
                {
                    "type": "final",
                    "content": json.dumps(
                        {"answer": "答案正文。", "citations": [2]},
                        ensure_ascii=False,
                    ),
                }
            ]
        )

        result = agent.answer("裁剪")

        self.assertIn("答案正文。", result)
        self.assertEqual(agent.last_citations, (2,))
        self.assertTrue(agent.last_structured)
        # 只列模型真正引用的第 2 段，不把第 1 段也贴上去。
        self.assertIn("来源：[2]", result)
        self.assertIn("乙", result)
        self.assertNotIn("[1]", result)

    def test_falls_back_to_plain_text_when_model_ignores_schema(self) -> None:
        agent = self._agent([{"type": "final", "content": "这是一段自由文本。"}])

        result = agent.answer("裁剪")

        self.assertIn("这是一段自由文本。", result)
        self.assertFalse(agent.last_structured)
        self.assertIsNone(agent.last_citations)
        # 退回自由文本时，来源清单恢复到"列出全部片段"。
        self.assertIn("来源：[1]", result)


class NoteAnswerTest(unittest.TestCase):
    def test_used_filters_out_of_range_and_duplicate_indices(self) -> None:
        answer = NoteAnswer(answer="正文", citations=[0, 1, 9, 2, 2])

        self.assertEqual(answer.used(3), (1, 2))

    def test_rejects_empty_answer(self) -> None:
        with self.assertRaises(ValidationError):
            NoteAnswer(answer="")


class NoteChunkTest(unittest.TestCase):
    def test_citation_without_line_number_is_just_the_source(self) -> None:
        chunk = NoteChunk(source="a.md", heading="标题", content="正文")

        self.assertEqual(chunk.citation(), "a.md")
        self.assertIn("[片段 3]", chunk.segment(3))
        self.assertIn("a.md", chunk.segment(3))


if __name__ == "__main__":
    unittest.main()