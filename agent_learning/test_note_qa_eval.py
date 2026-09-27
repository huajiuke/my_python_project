"""NoteQAAgent 评估接入（note_qa_eval.py）的测试。"""

import tempfile
import unittest
from pathlib import Path

from agent_learning.eval_harness import (
    EvalCase,
    Expectation,
    run_and_compare,
    run_suite,
)
from agent_learning.note_qa_eval import (
    EchoContextLLM,
    build_cases,
    make_runner,
)


SESSION_NOTE = "# SQLAlchemy Session\n\nSession 是会话对象，用完要 close。\n"
UNRELATED_NOTE = "# 其他\n\n这里讲的是完全不同的东西。\n"

SESSION_CASE = EvalCase(
    case_id="session",
    question="Session",
    expectation=Expectation(
        must_include=("Session",),
        must_not_include=("我无法确定",),
        expected_tools=("note_search",),
        max_tokens=3000,
    ),
)

NO_HIT_CASE = EvalCase(
    case_id="no-hit",
    question="zzzz",
    expectation=Expectation(must_include=("没有找到",)),
)


class TempNoteRoot(unittest.TestCase):
    """把一段笔记写进临时目录，当作可检索的笔记库。"""

    def write_note(self, text: str) -> str:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        (Path(directory.name) / "note.md").write_text(text, encoding="utf-8")
        return directory.name

    @staticmethod
    def offline_runner(root: str):
        return make_runner(
            [root],
            EchoContextLLM(),
            structured=True,
            context_budget=3000,
        )


class NoteQARunnerTest(TempNoteRoot):
    def test_offline_runner_passes_matching_cases(self) -> None:
        runner = self.offline_runner(self.write_note(SESSION_NOTE))

        report = run_suite([SESSION_CASE, NO_HIT_CASE], runner)

        self.assertEqual(report.passed, 2)
        self.assertEqual(report.failed, 0)

    def test_tokens_include_the_assembled_context(self) -> None:
        runner = self.offline_runner(self.write_note(SESSION_NOTE))

        outcome = run_suite([SESSION_CASE], runner).outcomes[0]

        # 答案只有几十个字符，token 数却要包含系统提示与笔记片段。
        self.assertGreater(outcome.tokens, 80)

    def test_no_hit_case_reports_no_tool_call(self) -> None:
        runner = self.offline_runner(self.write_note(SESSION_NOTE))

        outcome = run_suite([NO_HIT_CASE], runner).outcomes[0]

        self.assertTrue(outcome.passed)
        self.assertEqual(outcome.tool_calls, ())

    def test_regression_shows_up_when_notes_change(self) -> None:
        good_root = self.write_note(SESSION_NOTE)
        bad_root = self.write_note(UNRELATED_NOTE)
        with tempfile.TemporaryDirectory() as report_dir:
            report_path = Path(report_dir) / "baseline.json"
            first, _ = run_and_compare(
                [SESSION_CASE],
                self.offline_runner(good_root),
                report_path=report_path,
            )
            second, comparison = run_and_compare(
                [SESSION_CASE],
                self.offline_runner(bad_root),
                report_path=report_path,
            )

        self.assertEqual(first.failed, 0)
        self.assertEqual(second.failed, 1)
        self.assertEqual(second.regressions(first), ("session",))
        self.assertIn("回归: session", comparison)


class EchoContextLLMTest(unittest.TestCase):
    def test_extracts_notes_section_from_the_prompt(self) -> None:
        llm = EchoContextLLM()
        messages = [
            {"role": "system", "content": "系统提示"},
            {
                "role": "user",
                "content": "## 本地笔记片段\n\n片段正文\n\n## 问题\nSession",
            },
        ]

        answer = llm.decide(messages, [])

        self.assertIn("片段正文", answer["content"])
        self.assertNotIn("## 问题", answer["content"])

    def test_default_cases_are_runnable_and_unique(self) -> None:
        cases = build_cases()

        self.assertTrue(cases)
        self.assertEqual(
            len({case.case_id for case in cases}),
            len(cases),
        )


if __name__ == "__main__":
    unittest.main()