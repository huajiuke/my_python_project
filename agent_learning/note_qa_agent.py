"""本地笔记问答 Agent：先检索相关笔记，再让 LLM 回答并附上来源。

运行方式：
- python agent_learning/note_qa_agent.py "问题"   # Mock 离线演示
- python agent_learning/note_qa_agent.py --real "问题"
- python agent_learning/note_qa_agent.py --real --interactive
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

# 支持直接以 python agent_learning/note_qa_agent.py 运行时正常导入项目包。
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
            *history_messages,
            {
                "role": "user",
                "content": f"## 本地笔记片段\n\n{context}\n\n## 问题\n{question}",
            },
        ]

        assistant_msg = self.llm.decide(messages, [])
        answer = assistant_msg.get("content")
        if not isinstance(answer, str) or not answer.strip():
            return "模型未能生成有效回答，请重试。"
        return answer

    def _remember(self, question: str, answer_text: str) -> None:
        """把一轮问答写入历史，并限制保留最近若干轮。"""
        self.history.extend(
            [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer_text},
            ]
        )
        limit = self.max_history_rounds * 2
        self.history = self.history[-limit:]

    def _last_history_messages(self) -> list[dict[str, str]]:
        """返回最近若干轮历史，用于多轮追问时保持上下文。"""
        limit = self.max_history_rounds * 2
        return self.history[-limit:]

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
            return message

        history_messages = self._last_history_messages()
        answer = self._answer_with_context(
            question,
            results,
            history_messages,
        )
        self._remember(question, answer)
        return f"{answer}\n\n{self._source_footer(results)}"


def main() -> None:
    """命令行入口：支持 Mock、真实模型和交互式连续问答。"""
    load_dotenv()
    args = sys.argv[1:]

    if "--mock" in args:
        llm = MockLLM(
            [{"type": "final", "content": "Mock 回答：已根据笔记片段给出简要答案。"}]
        )
    else:
        # 默认走真实模型；需要 agent_learning/.env 或系统环境变量配置。
        llm = OpenAICompatibleLLM()

    agent = NoteQAAgent(searcher=NoteSearcher(), llm=llm)

    if "--interactive" in args:
        print("输入问题开始，输入 exit 退出。")
        while True:
            question = input("> ").strip()
            if question.lower() in {"exit", "quit"}:
                break
            print(agent.ask(question))
            print()
        return

    questions = [arg for arg in args if not arg.startswith("--")]
    question = questions[0] if questions else "SQLAlchemy 的 Session 应该怎么管理？"
    print(agent.answer(question))


if __name__ == "__main__":
    main()
