"""Tests for the evaluation harness and regression comparison."""

import tempfile
import unittest
from pathlib import Path

from agent_learning.eval_harness import (
    EvalCase,
    EvalReport,
    Expectation,
    RunResult,
    evaluate_case,
    run_and_compare,
    run_suite,
)


def case(case_id: str, **expectation: object) -> EvalCase:
    return EvalCase(
        case_id=case_id,
        question=f'问题 {case_id}',
        expectation=Expectation(**expectation),  # type: ignore[arg-type]
    )


def runner_from(mapping: dict[str, object]):
    def runner(eval_case: EvalCase) -> RunResult:
        outcome = mapping[eval_case.case_id]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome  # type: ignore[return-value]

    return runner


class EvaluateCaseTest(unittest.TestCase):
    def test_passes_without_expectations(self) -> None:
        outcome = evaluate_case(case('a'), RunResult(answer='随便'))

        self.assertTrue(outcome.passed)
        self.assertEqual(outcome.failures, ())

    def test_passes_when_required_text_present(self) -> None:
        outcome = evaluate_case(
            case('a', must_include=('缓存命中',)), RunResult(answer='提到缓存命中率')
        )

        self.assertTrue(outcome.passed)

    def test_fails_when_required_text_missing(self) -> None:
        outcome = evaluate_case(
            case('a', must_include=('缓存命中',)), RunResult(answer='别的内容')
        )

        self.assertFalse(outcome.passed)
        self.assertIn('缺少必需内容: 缓存命中', outcome.failures[0])

    def test_fails_when_forbidden_text_present(self) -> None:
        outcome = evaluate_case(
            case('a', must_not_include=('我不确定',)), RunResult(answer='我不确定答案')
        )

        self.assertFalse(outcome.passed)
        self.assertIn('出现禁止内容: 我不确定', outcome.failures[0])

    def test_checks_expected_tools(self) -> None:
        ok = evaluate_case(
            case('a', expected_tools=('search_notes',)),
            RunResult(answer='答案', tool_calls=('search_notes',)),
        )
        missing = evaluate_case(
            case('b', expected_tools=('search_notes',)),
            RunResult(answer='答案', tool_calls=('get_current_time',)),
        )

        self.assertTrue(ok.passed)
        self.assertFalse(missing.passed)
        self.assertIn('未调用工具: search_notes', missing.failures[0])

    def test_allows_extra_tool_calls(self) -> None:
        outcome = evaluate_case(
            case('a', expected_tools=('search_notes',)),
            RunResult(answer='答案', tool_calls=('search_notes', 'read_text_file')),
        )

        self.assertTrue(outcome.passed)

    def test_checks_token_budget(self) -> None:
        ok = evaluate_case(case('a', max_tokens=100), RunResult(tokens=100))
        over = evaluate_case(case('b', max_tokens=100), RunResult(tokens=101))

        self.assertTrue(ok.passed)
        self.assertFalse(over.passed)
        self.assertIn('超出 token 预算: 101 > 100', over.failures[0])

    def test_collects_multiple_failures(self) -> None:
        outcome = evaluate_case(
            case('a', must_include=('甲',), must_not_include=('乙',)),
            RunResult(answer='乙'),
        )

        self.assertEqual(len(outcome.failures), 2)

    def test_keeps_answer_and_tokens(self) -> None:
        outcome = evaluate_case(case('a'), RunResult(answer='答案', tokens=42))

        self.assertEqual(outcome.answer, '答案')
        self.assertEqual(outcome.tokens, 42)


class EvalCaseValidationTest(unittest.TestCase):
    def test_rejects_empty_case_id(self) -> None:
        with self.assertRaises(ValueError):
            EvalCase(case_id='  ', question='问题')

    def test_rejects_empty_question(self) -> None:
        with self.assertRaises(ValueError):
            EvalCase(case_id='a', question='  ')


class RunSuiteTest(unittest.TestCase):
    def test_aggregates_results(self) -> None:
        cases = [
            case('a', must_include=('甲',)),
            case('b', must_include=('乙',)),
        ]
        runner = runner_from(
            {'a': RunResult(answer='甲'), 'b': RunResult(answer='别的')}
        )

        report = run_suite(cases, runner)

        self.assertEqual(report.total, 2)
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 1)
        self.assertAlmostEqual(report.pass_rate, 0.5)

    def test_rejects_duplicate_case_ids(self) -> None:
        with self.assertRaises(ValueError):
            run_suite([case('a'), case('a')], runner_from({'a': RunResult()}))

    def test_runner_error_becomes_failure(self) -> None:
        report = run_suite(
            [case('boom')], runner_from({'boom': RuntimeError('模型超时')})
        )

        outcome = report.outcomes[0]
        self.assertFalse(outcome.passed)
        self.assertIn('runner error: RuntimeError: 模型超时', outcome.failures[0])

    def test_empty_suite_has_zero_pass_rate(self) -> None:
        report = run_suite([], runner_from({}))

        self.assertEqual(report.total, 0)
        self.assertEqual(report.pass_rate, 0.0)


class EvalReportTest(unittest.TestCase):
    def test_summary_text(self) -> None:
        report = run_suite(
            [case('a', must_include=('甲',))], runner_from({'a': RunResult(answer='甲')})
        )

        self.assertIn('通过 1/1', report.summary())

    def test_total_tokens(self) -> None:
        report = run_suite(
            [case('a'), case('b')],
            runner_from({'a': RunResult(tokens=10), 'b': RunResult(tokens=32)}),
        )

        self.assertEqual(report.total_tokens, 42)

    def test_dict_round_trip(self) -> None:
        report = run_suite(
            [case('a', must_include=('甲',))], runner_from({'a': RunResult(answer='甲')})
        )

        restored = EvalReport.from_dict(report.to_dict())

        self.assertEqual(restored, report)

    def test_save_and_load(self) -> None:
        report = run_suite(
            [case('a', must_include=('甲',))],
            runner_from({'a': RunResult(answer='甲', tokens=7)}),
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'reports' / 'baseline.json'

            saved = report.save(path)
            restored = EvalReport.load(path)
            self.assertTrue(saved.is_file())

        self.assertEqual(restored, report)

    def test_detects_regressions(self) -> None:
        baseline = run_suite([case('a')], runner_from({'a': RunResult(answer='甲')}))
        current = run_suite(
            [case('a', must_include=('甲',))], runner_from({'a': RunResult(answer='乙')})
        )

        self.assertEqual(current.regressions(baseline), ('a',))
        self.assertEqual(current.improvements(baseline), ())

    def test_detects_improvements(self) -> None:
        baseline = run_suite(
            [case('a', must_include=('甲',))], runner_from({'a': RunResult(answer='乙')})
        )
        current = run_suite(
            [case('a', must_include=('甲',))], runner_from({'a': RunResult(answer='甲')})
        )

        self.assertEqual(current.improvements(baseline), ('a',))
        self.assertEqual(current.regressions(baseline), ())

    def test_new_case_is_neither_regression_nor_improvement(self) -> None:
        baseline = run_suite([case('a')], runner_from({'a': RunResult()}))
        current = run_suite(
            [case('a'), case('b')],
            runner_from({'a': RunResult(), 'b': RunResult()}),
        )

        self.assertEqual(current.new_cases(baseline), ('b',))
        self.assertEqual(current.regressions(baseline), ())
        self.assertEqual(current.improvements(baseline), ())

    def test_compare_mentions_regression_and_improvement(self) -> None:
        baseline = run_suite(
            [case('a'), case('b', must_include=('甲',))],
            runner_from({'a': RunResult(), 'b': RunResult(answer='乙')}),
        )
        current = run_suite(
            [case('a', must_include=('甲',)), case('b', must_include=('甲',))],
            runner_from({'a': RunResult(answer='丙'), 'b': RunResult(answer='甲')}),
        )

        text = current.compare(baseline)

        self.assertIn('回归: a', text)
        self.assertIn('改进: b', text)
        self.assertIn('基线', text)


class RunAndCompareTest(unittest.TestCase):
    def test_first_run_creates_baseline_then_reports_regression(self) -> None:
        cases = [case('a', must_include=('甲',))]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'baseline.json'

            first_report, first_text = run_and_compare(
                cases, runner_from({'a': RunResult(answer='甲')}), report_path=path
            )
            second_report, second_text = run_and_compare(
                cases, runner_from({'a': RunResult(answer='乙')}), report_path=path
            )
            self.assertTrue(path.is_file())

        self.assertEqual(first_report.passed, 1)
        self.assertNotIn('回归', first_text)
        self.assertEqual(second_report.passed, 0)
        self.assertIn('回归: a', second_text)


if __name__ == '__main__':
    unittest.main()