"""本地笔记问答 Agent：先检索相关笔记，再让 LLM 回答并附上来源。

本模块是 agent_learning 四个主题的汇合点：

- 检索（retrieval.py）：Markdown 按标题切块 + SQLite FTS5(trigram) 索引，
  每个片段带 `文件:起始行`，可以直接引用回原文；
- 上下文工程（token_budget.py）：系统提示 / 历史摘要 / 历史对话 / 检索片段
  按优先级争抢同一份 token 预算，超预算时先丢低优先级的那一端；
- 结构化输出（structured_output.py，可选）：让模型返回 {answer, citations}，
  校验通过才知道它到底引用了哪几段，不配合就退回自由文本；
- 评估与回归（eval_harness.py + note_qa_eval.py）：用真实问题跑用例集，
  和基线报告对比出回归清单。

运行方式：
- python agent_learning/note_qa_agent.py "问题"   # Mock 离线演示
- python agent_learning/note_qa_agent.py --real "问题"
- python agent_learning/note_qa_agent.py --real --structured "问题"
- python agent_learning/note_qa_agent.py --real --interactive
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Sequence

# 支持直接以 python agent_learning/note_qa_agent.py 运行时正常导入项目包。
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import Field

from agent_learning.conversation_memory import (
    DEFAULT_MEMORY_DB,
    ConversationMemory,
)
from agent_learning.conversation_summarizer import ConversationSummarizer
from agent_learning.note_search import DEFAULT_NOTE_ROOTS, NoteSearcher
from agent_learning.retrieval import NoteIndex
from agent_learning.structured_output import (
    StrictModel,
    StructuredOutputError,
    structured_call,
)
from agent_learning.token_budget import (
    DROP_FROM_HEAD,
    BudgetReport,
    ContextLayer,
    plan_context,
)
from agent_learning.tool_calling_agent import (
    MockLLM,
    OpenAICompatibleLLM,
    load_dotenv,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INDEX_DB = _REPO_ROOT / "agent_learning" / "data" / "notes.db"

SYSTEM_PROMPT = (
    "你是一个基于用户本地学习笔记回答问题的助手。"
    "请主要依据提供的笔记内容作答，不要编造笔记里没有的事实；"
    "笔记不足时明确说明。回答应简洁、结构化，适合面试复习。"
)
SUMMARY_HEADER = "## 已压缩的历史对话摘要"
NO_MATCH_MESSAGE = (
    "本地笔记中没有找到与这个问题相关的内容，请换一种问法或补充笔记。"
)


class LLM(Protocol):
    """NoteQAAgent 需要的最小 LLM 接口，与现有 Agent 适配层兼容。"""

    def decide(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
    ) -> dict[str, object]:
        ...


class NoteAnswer(StrictModel):
    """结构化回答：正文 + 引用到的片段编号（从 1 起）。

    有了 citations，来源清单就能只列模型真正用到的段落，
    而不是把检索到的片段全部贴在答案后面。编号越界或重复会被过滤掉。
    """

    answer: str = Field(min_length=1)
    citations: list[int] = Field(default_factory=list)

    def used(self, total: int) -> tuple[int, ...]:
        """返回合法且去重后的引用编号。"""
        picked: list[int] = []
        for index in self.citations:
            if 1 <= index <= total and index not in picked:
                picked.append(index)
        return tuple(picked)


@dataclass(frozen=True)
class NoteChunk:
    """检索命中的一段笔记，是"检索结果"与"上下文片段"的统一表示。"""

    source: str
    heading: str
    content: str
    start_line: int | None = None

    def citation(self) -> str:
        """引用定位：FTS5 索引带行号，旧的关键词检索只能给文件路径。"""
        if self.start_line is None:
            return self.source
        return f"{self.source}:{self.start_line}"

    def segment(self, index: int) -> str:
        """拼进 Prompt 的片段：编号 + 文件 + 标题 + 正文。"""
        return "[片段 {}] 文件: {} | 标题: {}\n{}".format(
            index,
            short_source(self.source),
            self.heading,
            self.content,
        )


def short_source(source: str) -> str:
    """把绝对路径改成相对仓库路径，输出更易读。"""
    try:
        return str(Path(source).resolve().relative_to(_REPO_ROOT))
    except ValueError:
        return source

@dataclass
class NoteQAAgent:
    """基于本地 Markdown 笔记的最简 RAG 问答闭环。

    流程：问题 -> 检索 top 片段 -> 按 token 预算组装上下文 -> LLM 回答 -> 附来源。
    相比 Agent 主动决定是否调用工具，这里先检索再回答更稳定，
    适合笔记问答这类"必须依赖知识库"的任务。

    检索后端二选一：传 index（FTS5 索引，推荐）或用 searcher（每次全量重扫）。
    """

    searcher: NoteSearcher | None = None
    llm: LLM | None = None
    index: NoteIndex | None = None
    max_results: int = 3
    context_budget_tokens: int = 3000
    reserve_output_tokens: int = 800
    structured_answers: bool = False
    structured_attempts: int = 2
    history: list[dict[str, str]] = field(default_factory=list)
    max_history_rounds: int = 5
    memory: ConversationMemory | None = None
    session_id: str = "default"
    summarizer: ConversationSummarizer | None = None
    summary_trigger_rounds: int = 10
    last_budget_report: BudgetReport | None = field(
        default=None,
        init=False,
        repr=False,
    )
    last_chunks: tuple[NoteChunk, ...] = field(
        default=(),
        init=False,
        repr=False,
    )
    last_citations: tuple[int, ...] | None = field(
        default=None,
        init=False,
        repr=False,
    )
    last_structured: bool = field(default=False, init=False, repr=False)
    _summary: str | None = field(default=None, init=False, repr=False)
    _summary_pointer: int = field(default=0, init=False, repr=False)
    _unsummarized_history: list[dict[str, str]] = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        """Validate limits and restore recent messages for this session."""
        if self.llm is None:
            raise ValueError("llm is required")
        if self.searcher is None and self.index is None:
            self.searcher = NoteSearcher()
        if self.max_results < 1:
            raise ValueError("max_results must be at least 1")
        if self.context_budget_tokens < 1:
            raise ValueError("context_budget_tokens must be at least 1")
        if not 0 <= self.reserve_output_tokens <= self.context_budget_tokens:
            raise ValueError(
                "reserve_output_tokens must be between 0 "
                "and context_budget_tokens"
            )
        if self.structured_attempts < 1:
            raise ValueError("structured_attempts must be at least 1")
        if self.max_history_rounds < 1:
            raise ValueError("max_history_rounds must be at least 1")
        if self.summary_trigger_rounds < 1:
            raise ValueError("summary_trigger_rounds must be at least 1")
        if self.summarizer is not None:
            if self.memory is None:
                raise ValueError("summarizer requires persistent memory")
            if self.summary_trigger_rounds < self.max_history_rounds:
                raise ValueError(
                    "summary_trigger_rounds must be at least "
                    "max_history_rounds"
                )
        if self.memory is not None:
            if self.summarizer is None:
                self.history = self.memory.recent(
                    self.session_id,
                    self.max_history_rounds * 2,
                )
            else:
                summary = self.memory.latest_summary(self.session_id)
                if summary is not None:
                    self._summary = summary["summary"]
                    self._summary_pointer = summary[
                        "summarized_through_id"
                    ]
                self._unsummarized_history = [
                    {
                        "role": str(message["role"]),
                        "content": str(message["content"]),
                    }
                    for message in self.memory.messages_after(
                        self.session_id,
                        self._summary_pointer,
                    )
                ]
                self.history = self._unsummarized_history[
                    -(self.max_history_rounds * 2) :
                ]

    def _search(self, question: str) -> list[NoteChunk]:
        """检索相关片段：优先用 FTS5 索引，否则退回关键词检索。"""
        if not question.strip():
            return []
        if self.index is not None:
            return [
                NoteChunk(
                    source=hit.source,
                    heading=hit.heading,
                    content=hit.text,
                    start_line=hit.start_line,
                )
                for hit in self.index.search(question, limit=self.max_results)
            ]
        searcher = self.searcher
        if searcher is None:  # __post_init__ 已兜底，这里只是收窄类型
            return []
        return [
            NoteChunk(
                source=str(item["source"]),
                heading=str(item["heading"]),
                content=str(item["content"]),
            )
            for item in searcher.search(question)
        ]

    @staticmethod
    def _source_footer(
        chunks: Sequence[NoteChunk],
        citations: tuple[int, ...] | None = None,
    ) -> str:
        """生成答案末尾的来源清单，避免模型只答不引用。

        结构化回答给了 citations 时只列真正用到的片段；编号全部越界时
        退回列出全部，以免来源凭空消失。
        """
        numbered = list(enumerate(chunks, start=1))
        if citations:
            picked = [item for item in numbered if item[0] in citations]
            if picked:
                numbered = picked
        lines: list[str] = []
        for index, chunk in numbered:
            line = "[{}] {} | {}".format(index, chunk.citation(), chunk.heading)
            if line not in lines:
                lines.append(line)
        return "\n".join("来源：" + line for line in lines)

    def _assemble_messages(
        self,
        question: str,
        chunks: Sequence[NoteChunk],
        history_messages: Sequence[dict[str, str]],
        summary: str | None,
    ) -> list[dict[str, object]]:
        """按 token 预算分层组装 Prompt，并记下本次预算报告。

        优先级从高到低：系统提示（mandatory）> 检索片段 > 历史摘要 > 历史对话。
        丢的顺序是：先丢对话历史（drop_from=head，从最早的一端丢），再丢摘要，
        最后才动检索片段（drop_from=tail，从最不相关的一端丢）——片段是这个 Agent
        的立身之本，宁可丢历史也不能丢它。
        保证被丢掉的永远是最不重要的内容。
        """
        history_segments = [
            "{}: {}".format(message["role"], message["content"])
            for message in history_messages
        ]
        note_segments = [
            chunk.segment(index) for index, chunk in enumerate(chunks, start=1)
        ]
        layers = [
            ContextLayer(
                name="instructions",
                priority=0,
                segments=(SYSTEM_PROMPT,),
                mandatory=True,
            ),
            ContextLayer(
                name="summary",
                priority=2,
                segments=(
                    (SUMMARY_HEADER + "\n" + summary,) if summary else ()
                ),
            ),
            ContextLayer(
                name="history",
                priority=3,
                segments=history_segments,
                drop_from=DROP_FROM_HEAD,
            ),
            ContextLayer(
                name="notes",
                priority=1,
                segments=note_segments,
            ),
        ]
        plan = plan_context(
            layers,
            self.context_budget_tokens,
            reserve_output_tokens=self.reserve_output_tokens,
        )
        self.last_budget_report = plan.report

        kept = {
            layer.name: segments
            for layer, segments in zip(layers, plan.segments)
        }
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": "\n\n".join(kept["instructions"]) or SYSTEM_PROMPT,
            }
        ]
        if kept["summary"]:
            messages.append(
                {"role": "system", "content": "\n\n".join(kept["summary"])}
            )
        kept_history = len(kept["history"])
        if kept_history:
            # history 层丢头保尾，保留的就是最近 kept_history 条消息。
            messages.extend(list(history_messages)[-kept_history:])
        notes_text = (
            "\n\n".join(kept["notes"])
            if kept["notes"]
            else "（未检索到相关内容）"
        )
        messages.append(
            {
                "role": "user",
                "content": "## 本地笔记片段\n\n{}\n\n## 问题\n{}".format(
                    notes_text,
                    question,
                ),
            }
        )
        return messages

    def _generate_answer(
        self,
        messages: Sequence[dict[str, object]],
        total_chunks: int,
    ) -> tuple[str, tuple[int, ...] | None]:
        """向 LLM 要答案；开启结构化输出时顺带拿到引用编号。"""
        llm = self.llm
        if llm is None:  # __post_init__ 已校验，这里只是收窄类型
            return "模型未能生成有效回答，请重试。", None

        if self.structured_answers:
            try:
                response = structured_call(
                    llm,
                    NoteAnswer,
                    messages,
                    max_attempts=self.structured_attempts,
                )
            except StructuredOutputError:
                # 模型不配合结构化输出时退回自由文本，不影响可用性。
                self.last_structured = False
            else:
                self.last_structured = True
                return response.value.answer, response.value.used(total_chunks)

        answer = llm.decide(list(messages), [])
        content = answer.get("content") if isinstance(answer, dict) else None
        if not isinstance(content, str) or not content.strip():
            return "模型未能生成有效回答，请重试。", None
        return content, None

    def _remember(self, question: str, answer_text: str) -> None:
        """把一轮问答写入历史，并限制保留最近若干轮。"""
        messages = [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer_text},
        ]
        if self.memory is not None:
            self.memory.append_many(self.session_id, messages)
        if self.summarizer is not None:
            self._unsummarized_history.extend(messages)
        self.history.extend(messages)
        limit = self.max_history_rounds * 2
        self.history = self.history[-limit:]

    def _last_history_messages(self) -> list[dict[str, str]]:
        """返回最近若干轮历史，用于多轮追问时保持上下文。"""
        if self.summarizer is not None:
            return list(self._unsummarized_history)
        limit = self.max_history_rounds * 2
        return self.history[-limit:]

    def _maybe_summarize(self) -> None:
        """Compact old complete rounds while preserving the recent window."""
        if self.summarizer is None or self.memory is None:
            return

        try:
            messages = self.memory.messages_after(
                self.session_id,
                self._summary_pointer,
            )
            completed_message_count = (len(messages) // 2) * 2
            completed_rounds = completed_message_count // 2
            if completed_rounds < self.summary_trigger_rounds:
                return

            compact_count = (
                completed_message_count - self.max_history_rounds * 2
            )
            if compact_count <= 0:
                return

            compact_messages = messages[:compact_count]
            summary = self.summarizer.summarize(
                self._summary,
                compact_messages,
            )
            pointer = int(compact_messages[-1]["id"])
            self.memory.save_summary(
                self.session_id,
                summary,
                pointer,
            )
            self._summary = summary
            self._summary_pointer = pointer
            self._unsummarized_history = [
                {
                    "role": str(message["role"]),
                    "content": str(message["content"]),
                }
                for message in self.memory.messages_after(
                    self.session_id,
                    pointer,
                )
            ]
        except Exception:
            # Memory compression is best effort; the answer must still be
            # returned and the unsummarized window retried on a later turn.
            return

    def answer(self, question: str) -> str:
        """单轮回答，不修改历史；适合一次性调用和单元测试。"""
        chunks = self._search(question)
        self.last_chunks = tuple(chunks)
        self.last_citations = None
        if not chunks:
            return NO_MATCH_MESSAGE
        messages = self._assemble_messages(question, chunks, [], None)
        text, citations = self._generate_answer(messages, len(chunks))
        self.last_citations = citations
        return "{}\n\n{}".format(text, self._source_footer(chunks, citations))

    def ask(self, question: str) -> str:
        """多轮问答入口：保存历史，并在下一轮把历史交给 LLM。"""
        chunks = self._search(question)
        self.last_chunks = tuple(chunks)
        self.last_citations = None
        if not chunks:
            self._remember(question, NO_MATCH_MESSAGE)
            self._maybe_summarize()
            return NO_MATCH_MESSAGE

        messages = self._assemble_messages(
            question,
            chunks,
            self._last_history_messages(),
            self._summary,
        )
        text, citations = self._generate_answer(messages, len(chunks))
        self.last_citations = citations
        self._remember(question, text)
        self._maybe_summarize()
        return "{}\n\n{}".format(text, self._source_footer(chunks, citations))

def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI without mixing option values into the question list."""
    parser = argparse.ArgumentParser(description="本地笔记问答 Agent")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--real", action="store_true", help="使用真实模型")
    mode.add_argument("--mock", action="store_true", help="使用离线 Mock")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="进入连续问答模式",
    )
    parser.add_argument(
        "--session-id",
        default="default",
        help="持久化记忆会话标识",
    )
    parser.add_argument(
        "--memory-db",
        default=str(DEFAULT_MEMORY_DB),
        help="SQLite 记忆数据库路径",
    )
    parser.add_argument(
        "--summarize-memory",
        action="store_true",
        help="达到阈值后压缩较早的对话历史",
    )
    parser.add_argument(
        "--summary-trigger-rounds",
        type=int,
        default=10,
        help="未压缩历史达到多少轮后触发摘要",
    )
    parser.add_argument(
        "--recent-history-rounds",
        type=int,
        default=5,
        help="摘要压缩后保留的最近原始对话轮数",
    )
    parser.add_argument(
        "--index-db",
        default=str(DEFAULT_INDEX_DB),
        help="FTS5 索引数据库路径（:memory: 只建内存索引）",
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="不用 FTS5 索引，退回每次全量扫描的关键词检索",
    )
    parser.add_argument(
        "--rebuild-index",
        action="store_true",
        help="清空并重建 FTS5 索引",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="每次检索返回的片段数",
    )
    parser.add_argument(
        "--context-budget",
        type=int,
        default=3000,
        help="单次请求的上下文 token 预算",
    )
    parser.add_argument(
        "--reserve-output",
        type=int,
        default=800,
        help="为模型输出预留的 token 数",
    )
    parser.add_argument(
        "--structured",
        action="store_true",
        help="要求模型返回 answer/citations 结构，失败退回自由文本",
    )
    parser.add_argument("question", nargs="?", help="单次提问内容")
    return parser


def build_index(index_db: str, *, rebuild: bool = False) -> NoteIndex:
    """打开（必要时建立）FTS5 索引：索引为空就把默认笔记目录灌进去。"""
    index = NoteIndex(index_db)
    if rebuild:
        index.clear()
    if index.count() == 0:
        total = 0
        for root in DEFAULT_NOTE_ROOTS:
            if Path(root).is_dir():
                total += index.index_root(root)
        print("已建立索引：{} 个片段 -> {}".format(total, index_db))
    return index


def main() -> None:
    """命令行入口：支持 Mock、真实模型和持久化连续问答。"""
    load_dotenv()
    args = _build_parser().parse_args()

    if args.mock:
        llm = MockLLM(
            [{"type": "final", "content": "Mock 回答：已根据笔记片段给出简要答案。"}]
        )
    else:
        # 默认走真实模型；需要 agent_learning/.env 或系统环境变量配置。
        llm = OpenAICompatibleLLM()

    index = (
        None
        if args.no_index
        else build_index(args.index_db, rebuild=args.rebuild_index)
    )

    with ConversationMemory(args.memory_db) as memory:
        agent = NoteQAAgent(
            searcher=None if index is not None else NoteSearcher(),
            llm=llm,
            index=index,
            max_results=args.limit,
            context_budget_tokens=args.context_budget,
            reserve_output_tokens=args.reserve_output,
            structured_answers=args.structured,
            memory=memory,
            session_id=args.session_id,
            max_history_rounds=args.recent_history_rounds,
            summarizer=(
                ConversationSummarizer(llm)
                if args.summarize_memory
                else None
            ),
            summary_trigger_rounds=args.summary_trigger_rounds,
        )

        if args.interactive:
            print(
                f"输入问题开始，会话：{args.session_id}，输入 exit 退出。"
            )
            while True:
                question = input("> ").strip()
                if question.lower() in {"exit", "quit"}:
                    break
                print(agent.ask(question))
                print()
            return

        question = (
            args.question
            or "SQLAlchemy 的 Session 应该怎么管理？"
        )
        print(agent.ask(question))


if __name__ == "__main__":
    main()