"""最小 RAG Agent 示例：让 Agent 通过 search_notes 工具查询本地学习笔记。

默认使用 MockLLM 离线演示；加 --real 可切换为真实 OpenAI 兼容模型。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 支持直接以 python agent_learning/note_search_agent.py 运行时正常导入包。
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_learning.note_search import NoteSearcher, build_search_notes_tool
from agent_learning.tool_calling_agent import (
    Agent,
    MockLLM,
    OpenAICompatibleLLM,
    ToolRegistry,
)


def build_note_registry() -> ToolRegistry:
    """创建只包含本地笔记搜索工具的 Agent 工具注册表。"""
    registry = ToolRegistry()
    registry.register(build_search_notes_tool(NoteSearcher()))
    return registry


def main() -> None:
    registry = build_note_registry()

    if "--real" in sys.argv[1:]:
        # 真实模式：python -m agent_learning.note_search_agent --real
        llm = OpenAICompatibleLLM()
    else:
        # Mock 模式：先调用 search_notes，再给出最终回答，便于离线理解闭环。
        llm = MockLLM(
            [
                {
                    "type": "tool_call",
                    "name": "search_notes",
                    "arguments": {"query": "SQLAlchemy Session 管理"},
                },
                {
                    "type": "final",
                    "content": "根据笔记找到 SQLAlchemy Session 管理相关章节。",
                },
            ]
        )

    agent = Agent(llm=llm, tools=registry)
    answer = agent.run("SQLAlchemy 的 Session 应该怎么管理？")
    print(f"\n最终回答: {answer}")


if __name__ == "__main__":
    main()
