"""最小 RAG 检索工具：把本地 Markdown 笔记切块后按关键词检索。

学习目标：先不引入向量库，理解 RAG 的最小闭环：
文档 -> 切块 -> 检索 -> 把相关片段返回给 LLM。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from agent_learning.tool_calling_agent import Tool


# ---------- 常量与基础工具 ----------

_REPO_ROOT = Path(__file__).resolve().parent.parent

# 默认只检索 docs/ 和 obsidian/，不进入 .obsidian、venv、git 等目录。
DEFAULT_NOTE_ROOTS: tuple[str, ...] = (
    str(_REPO_ROOT / "docs"),
    str(_REPO_ROOT / "obsidian"),
)

_SKIP_DIR_NAMES = {
    ".git",
    ".obsidian",
    ".idea",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
}

# 简单分词：英文/数字按单词匹配，中文按连续字符串的二元组匹配。
_WORD_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)
_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")


def tokenize(text: str) -> list[str]:
    """把查询文本拆成可打分 token。

    英文整体匹配；中文用二元组匹配，避免“的、在、中”等常见单字误召回。
    例如“SQLAlchemy Session 管理”会拆成 [sqlalchemy, session, 管理]。
    """
    text_lower = text.lower()
    tokens = [token.lower() for token in _WORD_RE.findall(text_lower)]
    for cjk_text in _CJK_RE.findall(text_lower):
        if len(cjk_text) == 1:
            tokens.append(cjk_text)
        else:
            tokens.extend(
                cjk_text[index : index + 2]
                for index in range(len(cjk_text) - 1)
            )
    return tokens


# ---------- 笔记切块与检索 ----------


@dataclass
class NoteSearcher:
    """读取一组 Markdown 目录，按 Markdown 标题切块并做关键词检索。"""

    roots: tuple[str, ...] = DEFAULT_NOTE_ROOTS
    max_results: int = 3
    max_chars: int = 500

    def _iter_markdown_files(self) -> list[Path]:
        """收集所有可检索的 .md 文件，按路径排序保证结果稳定。"""
        files: list[Path] = []
        for root in self.roots:
            path = Path(root)
            if not path.exists():
                continue
            for file in sorted(path.rglob("*.md")):
                if any(part in _SKIP_DIR_NAMES for part in file.parts):
                    continue
                files.append(file)
        return files

    def _split_into_chunks(self, file: Path) -> list[dict[str, str]]:
        """按标题把单个 Markdown 文件切块，便于后续检索与引用。"""
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        chunks: list[dict[str, str]] = []
        current_heading = file.name
        current_lines: list[str] = []

        def flush() -> None:
            """把当前标题下的内容保存为一块。"""
            content = "\n".join(current_lines).strip()
            if content:
                chunks.append(
                    {
                        "source": str(file),
                        "heading": current_heading,
                        "content": content[: self.max_chars],
                    }
                )

        for line in text.splitlines():
            if line.startswith("#"):
                flush()
                current_heading = line.lstrip("#").strip() or file.name
                current_lines = []
            else:
                current_lines.append(line)
        flush()
        return chunks

    def chunks(self) -> list[dict[str, str]]:
        """实时扫描全部 Markdown 切块，保证笔记更新后 Agent 能检索到新内容。"""
        loaded: list[dict[str, str]] = []
        for file in self._iter_markdown_files():
            loaded.extend(self._split_into_chunks(file))
        return loaded

    def search(self, query: str) -> list[dict[str, str]]:
        """按查询 token 出现次数排序，返回最相关的一批切块。"""
        tokens = tokenize(query)
        if not tokens:
            return []

        scored: list[tuple[int, dict[str, str]]] = []
        for chunk in self.chunks():
            # 标题也参与打分，但只把内容返回给 LLM，保持 Observation 精简。
            searchable = f"{chunk['heading']}\n{chunk['content']}".lower()
            score = sum(searchable.count(token) for token in tokens)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[: self.max_results]]

    @staticmethod
    def format_results(results: list[dict[str, str]]) -> str:
        """把检索结果转成 Observation JSON，供 LLM 读取和引用。"""
        if not results:
            return json.dumps(
                {"message": "没有找到相关笔记，请尝试更换关键词。"},
                ensure_ascii=False,
            )
        return json.dumps(
            {"results": results},
            ensure_ascii=False,
            indent=2,
        )


# ---------- 工具注册 ----------


def build_search_notes_tool(searcher: NoteSearcher | None = None) -> Tool:
    """把本地笔记检索能力封装成 Agent 可调用的 search_notes 工具。"""
    note_searcher = searcher or NoteSearcher()

    def search_notes(query: str) -> str:
        """搜索 docs/ 与 obsidian/ 中的 Markdown 笔记并返回相关片段。"""
        return note_searcher.format_results(note_searcher.search(query))

    return Tool(
        name="search_notes",
        description="搜索本地 Python/后端/AI 学习笔记，返回最相关的 Markdown 片段",
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "要搜索的主题或关键词，例如 SQLAlchemy Session 管理",
                },
            },
            "required": ["query"],
        },
        handler=search_notes,
    )
