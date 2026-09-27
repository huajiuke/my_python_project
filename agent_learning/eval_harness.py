"""评估与回归：把"感觉变好了"变成可验证的数字。

改 prompt、换模型、动检索参数之后，必须能回答两个问题：

1. **现在好不好**：关键事实保留率、工具调用正确率、token 成本；
2. **比上次好还是坏**：和上一次的报告对比，找出**回归**的具体用例。

设计要点：

- 用例是**可执行的检查**（必须包含/禁止包含哪些字串、是否调用了某工具、token 上限），
  而不是主观打分——主观打分无法进 CI，也无法定位回归；
- 报告可序列化，作为**基线**存档，下次运行直接对比；
- 跑挂了（抛异常）也算用例失败，而不是让整轮回归中断。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence


@dataclass(frozen=True)
class Expectation:
    """一条用例的验收标准。"""

    must_include: tuple[str, ...] = ()
    must_not_include: tuple[str, ...] = ()
    expected_tools: tuple[str, ...] = ()
    max_tokens: int | None = None


@dataclass(frozen=True)
class EvalCase:
    """一条评估用例：给 Agent 的任务 + 验收标准。"""

    case_id: str
    question: str
    expectation: Expectation = field(default_factory=Expectation)

    def __post_init__(self) -> None:
        if not self.case_id.strip():
            raise ValueError('case_id must not be empty')
        if not self.question.strip():
            raise ValueError('question must not be empty')


@dataclass(frozen=True)
class RunResult:
    """被测系统返回的结果。"""

    answer: str = ''
    tool_calls: tuple[str, ...] = ()
    tokens: int = 0


class EvalRunner(Protocol):
    """把一条用例跑成一个结果。"""

    def __call__(self, case: EvalCase) -> RunResult:
        ...


@dataclass(frozen=True)
class CaseOutcome:
    """一条用例的执行结论。"""

    case_id: str
    passed: bool
    failures: tuple[str, ...] = ()
    answer: str = ''
    tool_calls: tuple[str, ...] = ()
    tokens: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            'case_id': self.case_id,
            'passed': self.passed,
            'failures': list(self.failures),
            'answer': self.answer,
            'tool_calls': list(self.tool_calls),
            'tokens': self.tokens,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'CaseOutcome':
        return cls(
            case_id=str(payload['case_id']),
            passed=bool(payload['passed']),
            failures=tuple(payload.get('failures', ())),
            answer=str(payload.get('answer', '')),
            tool_calls=tuple(payload.get('tool_calls', ())),
            tokens=int(payload.get('tokens', 0)),
        )


def evaluate_case(case: EvalCase, result: RunResult) -> CaseOutcome:
    """按用例的验收标准判定结果。"""
    failures: list[str] = []
    answer = result.answer or ''
    expectation = case.expectation

    for text in expectation.must_include:
        if text not in answer:
            failures.append(f'缺少必需内容: {text}')
    for text in expectation.must_not_include:
        if text in answer:
            failures.append(f'出现禁止内容: {text}')
    for tool in expectation.expected_tools:
        if tool not in result.tool_calls:
            failures.append(f'未调用工具: {tool}')
    if expectation.max_tokens is not None and result.tokens > expectation.max_tokens:
        failures.append(
            f'超出 token 预算: {result.tokens} > {expectation.max_tokens}'
        )

    return CaseOutcome(
        case_id=case.case_id,
        passed=not failures,
        failures=tuple(failures),
        answer=answer,
        tool_calls=tuple(result.tool_calls),
        tokens=result.tokens,
    )


@dataclass(frozen=True)
class EvalReport:
    """一次完整评估的结果，可作为下次的基线。"""

    outcomes: tuple[CaseOutcome, ...]

    @property
    def total(self) -> int:
        return len(self.outcomes)

    @property
    def passed(self) -> int:
        return sum(1 for outcome in self.outcomes if outcome.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def pass_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def total_tokens(self) -> int:
        return sum(outcome.tokens for outcome in self.outcomes)

    def failing_cases(self) -> tuple[CaseOutcome, ...]:
        return tuple(outcome for outcome in self.outcomes if not outcome.passed)

    def summary(self) -> str:
        return (
            f'通过 {self.passed}/{self.total}（{self.pass_rate:.0%}）'
            f' 失败 {self.failed} 总 token {self.total_tokens}'
        )

    def to_dict(self) -> dict[str, Any]:
        return {'outcomes': [outcome.to_dict() for outcome in self.outcomes]}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> 'EvalReport':
        return cls(
            outcomes=tuple(
                CaseOutcome.from_dict(item) for item in payload.get('outcomes', ())
            )
        )

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        return target

    @classmethod
    def load(cls, path: str | Path) -> 'EvalReport':
        return cls.from_dict(
            json.loads(Path(path).read_text(encoding='utf-8'))
        )

    def _pass_map(self) -> dict[str, bool]:
        return {outcome.case_id: outcome.passed for outcome in self.outcomes}

    def regressions(self, previous: 'EvalReport') -> tuple[str, ...]:
        """上次通过、这次失败的用例——最需要立刻关注的部分。"""
        before = previous._pass_map()
        return tuple(
            outcome.case_id
            for outcome in self.outcomes
            if before.get(outcome.case_id) is True and not outcome.passed
        )

    def improvements(self, previous: 'EvalReport') -> tuple[str, ...]:
        """上次失败、这次通过的用例。"""
        before = previous._pass_map()
        return tuple(
            outcome.case_id
            for outcome in self.outcomes
            if before.get(outcome.case_id) is False and outcome.passed
        )

    def new_cases(self, previous: 'EvalReport') -> tuple[str, ...]:
        """基线里没有的用例（新增用例不算回归，也不算改进）。"""
        before = previous._pass_map()
        return tuple(
            outcome.case_id
            for outcome in self.outcomes
            if outcome.case_id not in before
        )

    def compare(self, previous: 'EvalReport') -> str:
        """给出与基线的对比，用于日志或 PR 评论。"""
        parts = [
            self.summary(),
            f'基线 {previous.summary()}',
        ]
        regressions = self.regressions(previous)
        improvements = self.improvements(previous)
        parts.append(
            '回归: ' + (', '.join(regressions) if regressions else '无')
        )
        parts.append(
            '改进: ' + (', '.join(improvements) if improvements else '无')
        )
        new_cases = self.new_cases(previous)
        if new_cases:
            parts.append('新增用例: ' + ', '.join(new_cases))
        return ' | '.join(parts)


def run_suite(
    cases: Sequence[EvalCase],
    runner: EvalRunner,
) -> EvalReport:
    """跑完整个用例集，单个用例抛异常只记为失败，不中断整轮。"""
    seen: set[str] = set()
    outcomes: list[CaseOutcome] = []
    for case in cases:
        if case.case_id in seen:
            raise ValueError(f'duplicate case_id: {case.case_id}')
        seen.add(case.case_id)
        try:
            result = runner(case)
        except Exception as exc:  # noqa: BLE001 - 评估必须跑完整轮
            outcomes.append(
                CaseOutcome(
                    case_id=case.case_id,
                    passed=False,
                    failures=(f'runner error: {type(exc).__name__}: {exc}',),
                )
            )
            continue
        outcomes.append(evaluate_case(case, result))
    return EvalReport(tuple(outcomes))


def run_and_compare(
    cases: Sequence[EvalCase],
    runner: EvalRunner,
    *,
    report_path: str | Path,
) -> tuple[EvalReport, str]:
    """跑一轮评估，与 ``report_path`` 的基线对比，并写回新报告。"""
    report = run_suite(cases, runner)
    target = Path(report_path)
    previous = EvalReport.load(target) if target.exists() else None
    comparison = report.compare(previous) if previous else report.summary()
    report.save(target)
    return report, comparison