"""本地笔记问答 Agent：先检索相关笔记，再让 LLM 回答并附上来源。

运行方式：
- python agent_learning/note_qa_agent.py "问题"   # Mock 离线演示
- python agent_learning/note_qa_agent.py --real "问题"
- python agent_learning/note_qa_agent.py --real --interactive
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

# 支持直接以 python agent_learning/note_qa_agent.py 运行时正常导入项目包。
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_learning.conversation_memory import (
    DEFAULT_MEMORY_DB,
    ConversationMemory,
)
from agent_learning.conversation_summarizer import ConversationSummarizer
from agent_learning.note_search import NoteSearcher
from agent_learning.tool_calling_agent import (
    MockLLM,
    OpenAICompatibleLLM,
    load_dotenv,
)


_REPO_ROOT = Path(__file__).resolve().parent.parent


class LLM(Protocol):
    """NoteQAAgent 需要的最小 LLM 接口，与现有 Agent 适配层兼容。"""

    def decide(
        self,
        messages: list[dict[str, object]],
        tools: list[dict[str, object]],
    ) -> dict[str, object]:
        ...


@dataclass
class NoteQAAgent:
    """基于本地 Markdown 笔记的最简 RAG 问答闭环。

    流程：问题 -> 关键词检索 top 片段 -> 拼成带来源的上下文 -> LLM 回答。
    相比 Agent 主动决定是否调用工具，这里先检索再回答更稳定，
    适合笔记问答这类"必须依赖知识库"的任务。
    """

    searcher: NoteSearcher
    llm: LLM
    history: list[dict[str, str]] = field(default_factory=list)
    max_history_rounds: int = 5
    memory: ConversationMemory | None = None
    session_id: str = "default"
    summarizer: ConversationSummarizer | None = None
    summary_trigger_rounds: int = 10
    _summary: str | None = field(default=None, init=False, repr=False)
    _summary_pointer: int = field(default=0, init=False, repr=False)
    _unsummarized_history: list[dict[str, str]] = field(
        default_factory=list,
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        """Validate limits and restore recent messages for this session."""
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

    @staticmethod
    def _short_source(source: str) -> str:
        """把绝对路径改成相对仓库路径，输出更易读。"""
        try:
            return str(Path(source).resolve().relative_to(_REPO_ROOT))
        except ValueError:
            return source

    @classmethod
    def _format_context(cls, results: list[dict[str, str]]) -> str:
        """把检索片段格式化成带编号、文件和标题的上下文。"""
        blocks = []
        for index, result in enumerate(results, start=1):
            blocks.append(
                "[片段 {}] 文件: {} | 标题: {}\n{}".format(
                    index,
                    cls._short_source(result["source"]),
                    result["heading"],
                    result["content"],
                )
            )
        return "\n\n".join(blocks)

    @staticmethod
    def _source_footer(results: list[dict[str, str]]) -> str:
        """生成答案末尾的来源清单，避免模型只答不引用。"""
        sources = []
        for result in results:
            line = "{} | {}".format(
                NoteQAAgent._short_source(result["source"]),
                result["heading"],
            )
            if line not in sources:
                sources.append(line)
        return "\n".join("来源：" + source for source in sources)

    def _answer_with_context(
        self,
        question: str,
        results: list[dict[str, str]],
        history_messages: list[dict[str, str]],
        summary: str | None = None,
    ) -> str:
        """把检索片段和历史对话一起发给 LLM，返回原始模型回答。"""
        context = self._format_context(results)
        messages: list[dict[str, object]] = [
            {
                "role": "system",
                "content": (
                    "你是一个基于用户本地学习笔记回答问题的助手。"
                    "请主要依据提供的笔记内容作答，不要编造笔记里没有的事实；"
                    "笔记不足时明确说明。回答应简洁、结构化，适合面试复习。"
                ),
            },
        ]
        if summary:
            messages.append(
                {
                    "role": "system",
                    "content": f"## 已压缩的历史对话摘要\n{summary}",
                }
            )
        messages.extend(history_messages)
        messages.append(
            {
                "role": "user",
                "content": f"## 本地笔记片段\n\n{context}\n\n## 问题\n{question}",
            }
        )

        assistant_msg = self.llm.decide(messages, [])
        answer = assistant_msg.get("content")
        if not isinstance(answer, str) or not answer.strip():
            return "模型未能生成有效回答，请重试。"
        return answer

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
        results = self.searcher.search(question)
        if not results:
            return "本地笔记中没有找到与这个问题相关的内容，请换一种问法或补充笔记。"
        answer = self._answer_with_context(question, results, [])
        return f"{answer}\n\n{self._source_footer(results)}"

    def ask(self, question: str) -> str:
        """多轮问答入口：保存历史，并在下一轮把历史交给 LLM。"""
        results = self.searcher.search(question)
        if not results:
            message = (
                "本地笔记中没有找到与这个问题相关的内容，请换一种问法或补充笔记。"
            )
            self._remember(question, message)
            self._maybe_summarize()
            return message

        history_messages = self._last_history_messages()
        answer = self._answer_with_context(
            question,
            results,
            history_messages,
            self._summary,
        )
        self._remember(question, answer)
        self._maybe_summarize()
        return f"{answer}\n\n{self._source_footer(results)}"


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
    parser.add_argument("question", nargs="?", help="单次提问内容")
    return parser


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

    with ConversationMemory(args.memory_db) as memory:
        agent = NoteQAAgent(
            searcher=NoteSearcher(),
            llm=llm,
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
