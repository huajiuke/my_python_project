"""笔记问答 Agent：检索 -> 回答 -> 附来源的最小 RAG 闭环测试。"""

import sqlite3
import unittest
from pathlib import Path

from agent_learning.conversation_memory import ConversationMemory
from agent_learning.note_qa_agent import NoteQAAgent
from agent_learning.note_search import NoteSearcher
from agent_learning.tool_calling_agent import MockLLM


NOTE_ROOT = Path(__file__).resolve().parent / "fixtures" / "note_root"


class NoteQAAgentTest(unittest.TestCase):
    def test_answer_includes_retrieved_source(self) -> None:
        llm = MockLLM(
            [
                {
                    "type": "final",
                    "content": "Session 是数据库会话的核心对象。",
                }
            ]
        )
        agent = NoteQAAgent(
            searcher=NoteSearcher(roots=(str(NOTE_ROOT),)),
            llm=llm,
        )

        result = agent.answer("Session 管理")

        self.assertIn("Session 是数据库会话的核心对象", result)
        self.assertIn("来源：", result)
        self.assertIn("sqlalchemy.md", result)

    def test_answer_handles_no_match(self) -> None:
        llm = MockLLM(
            [
                {
                    "type": "final",
                    "content": "这条回答不应该被调用。",
                }
            ]
        )
        agent = NoteQAAgent(
            searcher=NoteSearcher(roots=(str(NOTE_ROOT),)),
            llm=llm,
        )

        result = agent.answer("完全不存在的主题")

        self.assertIn("没有找到", result)
        self.assertNotIn("这条回答", result)

    def test_followup_keeps_conversation_history(self) -> None:
        llm = MockLLM(
            [
                {
                    "type": "final",
                    "content": "Session 是数据库会话的核心对象。",
                },
                {
                    "type": "final",
                    "content": "flush 会把 SQL 发给数据库，commit 才提交事务。",
                },
            ]
        )
        agent = NoteQAAgent(
            searcher=NoteSearcher(roots=(str(NOTE_ROOT),)),
            llm=llm,
        )

        agent.ask("Session 管理")
        second_answer = agent.ask("那 flush 和 commit 有什么区别？")

        self.assertEqual(len(agent.history), 4)
        self.assertIn("commit", second_answer)
        second_request = llm.seen_messages[1]
        request_text = "\n".join(
            str(message.get("content"))
            for message in second_request
            if message.get("role") != "system"
        )
        self.assertIn("Session 管理", request_text)

    def test_history_is_limited_to_recent_rounds(self) -> None:
        llm = MockLLM(
            [{"type": "final", "content": "Mock 回答。"}]
        )
        agent = NoteQAAgent(
            searcher=NoteSearcher(roots=(str(NOTE_ROOT),)),
            llm=llm,
            max_history_rounds=1,
        )

        agent.ask("第一轮 Session 管理")
        agent.ask("第二轮 Session 管理")
        agent.ask("第三轮 Session 管理")

        self.assertEqual(len(agent.history), 2)
        self.assertEqual(agent.history[0]["content"], "第三轮 Session 管理")

    def test_ask_persists_question_and_answer(self) -> None:
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        memory = ConversationMemory(connection=connection)
        agent = NoteQAAgent(
            searcher=NoteSearcher(roots=(str(NOTE_ROOT),)),
            llm=MockLLM(
                [{"type": "final", "content": "Session 管理回答"}]
            ),
            memory=memory,
            session_id="session-1",
        )

        agent.ask("Session 管理")

        self.assertEqual(
            memory.recent("session-1", limit=10),
            [
                {"role": "user", "content": "Session 管理"},
                {"role": "assistant", "content": "Session 管理回答"},
            ],
        )

    def test_new_agent_restores_persisted_history(self) -> None:
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        memory = ConversationMemory(connection=connection)
        first_agent = NoteQAAgent(
            searcher=NoteSearcher(roots=(str(NOTE_ROOT),)),
            llm=MockLLM(
                [{"type": "final", "content": "第一轮回答"}]
            ),
            memory=memory,
            session_id="session-1",
        )
        first_agent.ask("Session 管理")

        second_llm = MockLLM(
            [{"type": "final", "content": "第二轮回答"}]
        )
        second_agent = NoteQAAgent(
            searcher=NoteSearcher(roots=(str(NOTE_ROOT),)),
            llm=second_llm,
            memory=memory,
            session_id="session-1",
        )
        second_agent.ask("那 flush 和 commit 有什么区别？")

        request_text = "\n".join(
            str(message.get("content"))
            for message in second_llm.seen_messages[0]
            if message.get("role") != "system"
        )
        self.assertIn("Session 管理", request_text)
        self.assertEqual(len(second_agent.history), 4)

    def test_answer_does_not_persist_history(self) -> None:
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        memory = ConversationMemory(connection=connection)
        agent = NoteQAAgent(
            searcher=NoteSearcher(roots=(str(NOTE_ROOT),)),
            llm=MockLLM(
                [{"type": "final", "content": "单轮回答"}]
            ),
            memory=memory,
            session_id="session-1",
        )

        agent.answer("Session 管理")

        self.assertEqual(memory.recent("session-1", limit=10), [])


if __name__ == "__main__":
    unittest.main()
