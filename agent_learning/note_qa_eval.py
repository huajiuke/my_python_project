"""把评估与回归（eval_harness.py）真正用到 NoteQAAgent 上。

改 prompt、换模型、调 --limit / --context-budget 之后，得有办法回答两个问题：
现在好不好、比上次好还是坏。落到这个 Agent 上是三件事：

1. **用例**：真实问题 + 可执行验收（必须出现哪些术语、token 上限），不写主观打分；
2. **runner**：每个用例换一个干净 Agent（不共享历史），跑一轮包成 RunResult；
3. **基线**：报告存档，下次运行对比出回归 / 改进 / 新增用例三张清单。

两种跑法：

- ``--offline``：用"回显检索上下文"的假模型，不需要 API Key。
  它验证的是**检索与上下文组装**有没有退化，不验证语言质量；
- ``--real``：用真实模型，验证端到端回答。

用法（建议在笔记所在的仓库根目录运行，这样 obsidian/ 与 docs/ 都能索引到）：

- python agent_learning/note_qa_eval.py --offline
- python agent_learning/note_qa_eval.py --real --report agent_learning/data/eval_baseline.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

# 支持直接以 python agent_learning/note_qa_eval.py 运行时正常导入项目包。
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_learning.eval_harness import (
    EvalCase,
    Expectation,
    RunResult,
    run_and_compare,
)
from agent_learning.note_qa_agent import NoteQAAgent
from agent_learning.note_search import DEFAULT_NOTE_ROOTS
from agent_learning.retrieval import NoteIndex
from agent_learning.token_budget import estimate_tokens
from agent_learning.tool_calling_agent import OpenAICompatibleLLM, load_dotenv


_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORT = _REPO_ROOT / "agent_learning" / "data" / "eval_baseline.json"
NO_MATCH_PREFIX = "没有找到"


class EchoContextLLM:
    """离线对照用假模型：把检索到的笔记片段原样当成答案。

    它不懂语言，但足以验证"有没有检索到、上下文组装对不对"，
    让评估在没有 API Key 时也能跑。返回 JSON 是为了同时走通结构化输出那条路。
    """

    def __init__(self) -> None:
        self.seen_messages: list[list[dict[str, Any]]] = []

    def decide(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self.seen_messages.append(messages)
        context = self._extract_context(messages)
        payload = {"answer": context or "（没有检索到笔记片段）", "citations": []}
        return {
            "role": "assistant",
            "content": json.dumps(payload, ensure_ascii=False),
        }

    @staticmethod
    def _extract_context(messages: Sequence[dict[str, Any]]) -> str:
        """从最后一条带笔记片段的 user 消息里取出上下文正文。"""
        for message in reversed(messages):
            content = message.get("content")
            if not isinstance(content, str) or "## 本地笔记片段" not in content:
                continue
            body = content.split("## 本地笔记片段", 1)[1]
            body = body.split("## 问题", 1)[0]
            return body.strip()
        return ""


def build_cases() -> tuple[EvalCase, ...]:
    """默认用例集：每个主题一条，外加一条"检索不到要老实说"。

    验收标准写成"必须出现的关键术语"：术语错了就说明检索没命中对的段落，
    或者模型答偏了——这类错误可以自动发现，不需要人读全文。
    """

    return (
        EvalCase(
            case_id="fts5-trigram",
            question="SQLite FTS5 中文 分词器 trigram",
            expectation=Expectation(
                must_include=("trigram",),
                expected_tools=("note_search",),
                max_tokens=8000,
            ),
        ),
        EvalCase(
            case_id="context-budget",
            question="token 预算 分层 裁剪 上下文",
            expectation=Expectation(
                must_include=("预算",),
                expected_tools=("note_search",),
                max_tokens=8000,
            ),
        ),
        EvalCase(
            case_id="structured-output",
            question="结构化输出 校验 重试 Pydantic",
            expectation=Expectation(
                must_include=("校验",),
                expected_tools=("note_search",),
                max_tokens=8000,
            ),
        ),
        EvalCase(
            case_id="honest-when-no-hit",
            question="zzzz 不存在的主题 qqqq",
            expectation=Expectation(
                must_include=(NO_MATCH_PREFIX,),
                must_not_include=("trigram",),
            ),
        ),
    )

@dataclass
class NoteQARunner:
    """把 Agent 工厂包成 eval_harness 需要的 runner。

    每个用例都新建 Agent：上一轮的对话历史如果带进下一轮，
    结果就会依赖用例顺序，评估也就不可重复了。
    """

    agent_factory: Callable[[], NoteQAAgent]

    def __call__(self, case: EvalCase) -> RunResult:
        agent = self.agent_factory()
        answer = agent.answer(case.question)
        tokens = estimate_tokens(answer)
        if agent.last_budget_report is not None:
            # 上下文也要算钱：否则"答案很短但塞了 8000 token 上下文"看不出来。
            tokens += agent.last_budget_report.total_tokens
        return RunResult(
            answer=answer,
            tool_calls=("note_search",) if agent.last_chunks else (),
            tokens=tokens,
        )


def make_runner(
    note_roots: Sequence[str],
    llm: Any,
    *,
    structured: bool,
    context_budget: int,
    verbose: bool = False,
) -> NoteQARunner:
    """建一个共享的内存索引，每个用例换一个干净 Agent。"""
    index = NoteIndex(":memory:")
    total = 0
    for root in note_roots:
        if Path(root).is_dir():
            total += index.index_root(root)
    if verbose:
        print("已索引 {} 个片段：{}".format(total, " | ".join(note_roots)))
        if total == 0:
            print("警告：没有索引到任何笔记，请用 --note-root 指定笔记目录")

    def factory() -> NoteQAAgent:
        return NoteQAAgent(
            llm=llm,
            index=index,
            context_budget_tokens=context_budget,
            structured_answers=structured,
        )

    return NoteQARunner(agent_factory=factory)


def _build_parser() -> argparse.ArgumentParser:
    """命令行参数：跑法、笔记目录、基线路径、预算。"""
    parser = argparse.ArgumentParser(description="NoteQAAgent 评估与回归")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--offline",
        action="store_true",
        help="用回显检索上下文的假模型（默认，无需 API Key）",
    )
    mode.add_argument("--real", action="store_true", help="用真实模型")
    parser.add_argument(
        "--note-root",
        action="append",
        default=None,
        help="笔记目录，可重复传入；默认 docs/ 与 obsidian/",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help="基线报告路径，跑完会写回这里",
    )
    parser.add_argument(
        "--context-budget",
        type=int,
        default=3000,
        help="单次请求的上下文 token 预算",
    )
    parser.add_argument(
        "--structured",
        action="store_true",
        help="真实模型模式下要求返回 answer/citations 结构",
    )
    return parser


def main() -> None:
    """跑一遍用例集，与基线对比，并写回新报告。"""
    load_dotenv()
    args = _build_parser().parse_args()
    roots = tuple(args.note_root) if args.note_root else DEFAULT_NOTE_ROOTS

    llm: Any
    if args.real:
        llm = OpenAICompatibleLLM()
        structured = args.structured
    else:
        # 离线对照：假模型总是返回 JSON，顺带走通结构化输出那条路。
        llm = EchoContextLLM()
        structured = True

    runner = make_runner(
        roots,
        llm,
        structured=structured,
        context_budget=args.context_budget,
        verbose=True,
    )
    report, comparison = run_and_compare(
        build_cases(),
        runner,
        report_path=args.report,
    )

    for outcome in report.failing_cases():
        print("失败 {}：{}".format(outcome.case_id, "；".join(outcome.failures)))
    print(comparison)
    print("报告：{}".format(args.report))


if __name__ == "__main__":
    main()