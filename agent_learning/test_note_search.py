"""最小 RAG 检索工具与 search_notes 工具测试。"""

import json
import unittest
from pathlib import Path

from agent_learning.note_search import NoteSearcher, build_search_notes_tool
from agent_learning.tool_calling_agent import ToolRegistry


# 使用仓库内静态 fixture，避免测试依赖系统临时目录。
NOTE_ROOT = Path(__file__).resolve().parent / "fixtures" / "note_root"


class NoteSearcherTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = NOTE_ROOT

    def test_search_returns_relevant_section(self) -> None:
        searcher = NoteSearcher(roots=(str(self.root),))

        results = searcher.search("Session 管理")

        self.assertTrue(results)
        self.assertEqual(results[0]["heading"], "SQLAlchemy Session 管理")
        self.assertIn("Session 是数据库会话的核心对象", results[0]["content"])

    def test_search_returns_empty_when_no_match(self) -> None:
        searcher = NoteSearcher(roots=(str(self.root),))

        self.assertEqual(searcher.search("完全不存在的主题"), [])

    def test_ignores_hidden_obsidian_directory(self) -> None:
        searcher = NoteSearcher(roots=(str(self.root),))

        self.assertEqual(searcher.search("隐藏笔记"), [])

    def test_ignores_non_markdown_files(self) -> None:
        searcher = NoteSearcher(roots=(str(self.root),))

        self.assertEqual(searcher.search("这句话只存在于 txt 文件中"), [])

    def test_format_results_returns_json_message_when_empty(self) -> None:
        output = NoteSearcher.format_results([])

        self.assertIn("没有找到相关笔记", output)


class SearchNotesToolTest(unittest.TestCase):
    def test_tool_schema_and_handler(self) -> None:
        registry = ToolRegistry()
        registry.register(build_search_notes_tool(NoteSearcher(roots=(str(NOTE_ROOT),))))

        schemas = registry.schemas()
        self.assertEqual(schemas[0]["function"]["name"], "search_notes")
        self.assertIn("query", schemas[0]["function"]["parameters"]["properties"])

        observation = registry.call("search_notes", {"query": "Session 管理"})
        outer_body = json.loads(observation)
        payload = json.loads(outer_body["result"])
        self.assertIn("results", payload)
        self.assertEqual(payload["results"][0]["heading"], "SQLAlchemy Session 管理")


if __name__ == "__main__":
    unittest.main()
