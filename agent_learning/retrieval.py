"""Markdown 检索：按标题切块、SQLite FTS5 索引、段落级溯源。

对比 note_search.py（每次遍历文件 + 内存二元组计数），本模块补三件事：

1. **切块**：按 Markdown 标题切分并保留标题面包屑与行号，代码块不切断；
2. **索引**：持久化到 SQLite FTS5，用 bm25 排序，避免每次全量重扫；
3. **溯源**：每个结果都带 ``文件:起始行``，可以直接引用到原文。

中文检索的关键坑：FTS5 的 ``unicode61`` 分词器不切分中文，``MATCH '缓存'`` 查不到；
必须用 ``trigram`` 分词器（SQLite >= 3.34）。但 trigram 对**少于 3 字符**的查询无效，
所以短词回退到 LIKE 匹配。
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from agent_learning.token_budget import estimate_tokens, truncate_to_tokens


_HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$')
_FENCE_RE = re.compile(r'^\s*(```|~~~)')
_TERM_SPLIT_RE = re.compile(r'\s+')

# trigram 分词器无法匹配短于 3 个字符的查询词。
MIN_TRIGRAM_CHARS = 3
HEADING_BOOST = 2.0
# 拼接时每多一行就多一个换行符，必须计入预算，否则生成的块会超预算。
NEWLINE_TOKENS = 1
SKIP_DIR_NAMES = frozenset(
    {'.git', '.obsidian', '.idea', '__pycache__', '.venv', 'venv', 'node_modules'}
)


@dataclass(frozen=True)
class Chunk:
    """一段可检索的正文，带标题面包屑与行号范围。"""

    source: str
    heading: str
    start_line: int
    end_line: int
    text: str

    @property
    def tokens(self) -> int:
        return estimate_tokens(self.text)

    def citation(self) -> str:
        return f'{self.source}:{self.start_line}'


@dataclass(frozen=True)
class SearchHit:
    """一条检索结果，可直接拼进上下文。"""

    source: str
    heading: str
    start_line: int
    end_line: int
    text: str
    score: float

    def citation(self) -> str:
        return f'{self.source}:{self.start_line}'

    def snippet(self, max_chars: int = 160) -> str:
        flat = ' '.join(self.text.split())
        if len(flat) <= max_chars:
            return flat
        return flat[:max_chars] + '...'


def _join_lines(entries: Sequence[tuple[int, str]]) -> str:
    return '\n'.join(line for _, line in entries)


def _batches(
    entries: Sequence[tuple[int, str]],
    max_tokens: int,
) -> list[list[tuple[int, str]]]:
    """按 token 预算把行分批，且不在代码块中间断开。"""
    batches: list[list[tuple[int, str]]] = []
    current: list[tuple[int, str]] = []
    current_tokens = 0
    in_fence = False

    def flush() -> None:
        nonlocal current, current_tokens
        if current:
            batches.append(current)
        current = []
        current_tokens = 0

    for line_number, line in entries:
        is_fence = bool(_FENCE_RE.match(line))
        line_tokens = estimate_tokens(line) + (NEWLINE_TOKENS if current else 0)
        if (
            current
            and current_tokens + line_tokens > max_tokens
            and not in_fence
            and not is_fence
        ):
            flush()
            line_tokens = estimate_tokens(line)
        current.append((line_number, line))
        current_tokens += line_tokens
        if is_fence:
            in_fence = not in_fence

    flush()

    # 按行累加是近似值，逐块复核一次（每块一次估算），超预算就把末行留给下一块。
    # 含代码围栏的块不切：宁可稍微超预算，也不要把代码块拆开。
    checked: list[list[tuple[int, str]]] = []
    for batch in batches:
        has_fence = any(_FENCE_RE.match(line) for _, line in batch)
        if (
            len(batch) > 1
            and not has_fence
            and estimate_tokens(_join_lines(batch)) > max_tokens
        ):
            checked.append(batch[:-1])
            checked.append(batch[-1:])
        else:
            checked.append(batch)

    # 单行本身超预算：截断，保证不超过 max_tokens。
    for index, batch in enumerate(checked):
        if len(batch) == 1 and estimate_tokens(batch[0][1]) > max_tokens:
            line_number, line = batch[0]
            checked[index] = [(line_number, truncate_to_tokens(line, max_tokens))]
    return checked


def chunk_markdown(
    text: str,
    *,
    source: str = '',
    max_tokens: int = 400,
) -> tuple[Chunk, ...]:
    """按 Markdown 标题切块，超长小节再按 token 预算细分。

    超长小节按**行**边界切分（不在代码块内部切），
    单行超预算时用 ``truncate_to_tokens`` 截断。
    """
    if max_tokens < 1:
        raise ValueError('max_tokens must be at least 1')

    lines = text.splitlines()
    sections: list[tuple[tuple[str, ...], list[tuple[int, str]]]] = []
    heading_stack: list[tuple[int, str]] = []
    current: list[tuple[int, str]] = []
    in_fence = False

    def flush() -> None:
        nonlocal current
        if current:
            sections.append(
                (tuple(title for _, title in heading_stack), current)
            )
        current = []

    for line_number, line in enumerate(lines, start=1):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            current.append((line_number, line))
            continue
        match = None if in_fence else _HEADING_RE.match(line)
        if match:
            flush()
            level = len(match.group(1))
            heading_stack = [item for item in heading_stack if item[0] < level]
            heading_stack.append((level, match.group(2).strip()))
            current.append((line_number, line))
            continue
        current.append((line_number, line))
    flush()

    chunks: list[Chunk] = []
    for heading_path, entries in sections:
        for batch in _batches(entries, max_tokens):
            body = '\n'.join(line for _, line in batch).strip('\n')
            if not body:
                continue
            chunks.append(
                Chunk(
                    source=source,
                    heading=' > '.join(heading_path),
                    start_line=batch[0][0],
                    end_line=batch[-1][0],
                    text=body,
                )
            )
    return tuple(chunks)


def split_terms(query: str) -> list[str]:
    """把查询拆成检索词（按空白切分）。"""
    return [term for term in _TERM_SPLIT_RE.split(query.strip()) if term]


def _quote_fts_term(term: str) -> str:
    return '"' + term.replace('"', '""') + '"'


@dataclass
class NoteIndex:
    """SQLite FTS5 支撑的 Markdown 检索索引。"""

    database_path: str = ':memory:'
    max_tokens: int = 400

    def __post_init__(self) -> None:
        if self.max_tokens < 1:
            raise ValueError('max_tokens must be at least 1')
        if self.database_path != ':memory:':
            Path(self.database_path).expanduser().resolve().parent.mkdir(
                parents=True, exist_ok=True
            )
        self._connection = sqlite3.connect(self.database_path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS chunks USING fts5(
                text,
                source UNINDEXED,
                heading UNINDEXED,
                start_line UNINDEXED,
                end_line UNINDEXED,
                tokenize='trigram'
            )
            """
        )

    def close(self) -> None:
        self._connection.close()

    def count(self) -> int:
        row = self._connection.execute('SELECT count(*) AS total FROM chunks').fetchone()
        return int(row['total'])

    def clear(self) -> None:
        with self._connection:
            self._connection.execute('DELETE FROM chunks')

    def index_text(self, text: str, source: str) -> int:
        """索引一篇文档，返回写入的块数（同一 source 会被覆盖）。"""
        chunks = chunk_markdown(text, source=source, max_tokens=self.max_tokens)
        with self._connection:
            self._connection.execute('DELETE FROM chunks WHERE source = ?', (source,))
            self._connection.executemany(
                """
                INSERT INTO chunks (text, source, heading, start_line, end_line)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (chunk.text, chunk.source, chunk.heading, chunk.start_line, chunk.end_line)
                    for chunk in chunks
                ],
            )
        return len(chunks)

    def index_file(self, path: str | Path, *, root: str | Path | None = None) -> int:
        file_path = Path(path).resolve()
        if not file_path.is_file():
            raise FileNotFoundError(f'note file not found: {file_path}')
        relative = (
            file_path.relative_to(Path(root).resolve())
            if root is not None
            else file_path.name
        )
        return self.index_text(
            file_path.read_text(encoding='utf-8'), str(relative).replace('\\', '/')
        )

    def index_root(self, root: str | Path) -> int:
        """递归索引目录下的 Markdown 文件，返回总块数。"""
        root_path = Path(root).resolve()
        if not root_path.is_dir():
            raise NotADirectoryError(f'note root not found: {root_path}')
        total = 0
        for file_path in sorted(root_path.rglob('*.md')):
            if any(part in SKIP_DIR_NAMES for part in file_path.parts):
                continue
            total += self.index_file(file_path, root=root_path)
        return total

    def _rows_to_hits(
        self,
        rows: Sequence[sqlite3.Row],
        terms: Sequence[str],
        *,
        use_bm25: bool,
    ) -> list[SearchHit]:
        hits: list[SearchHit] = []
        for row in rows:
            text = str(row['text'])
            heading = str(row['heading'])
            if use_bm25:
                score = -float(row['score'])
            else:
                lowered_text = text.lower()
                score = float(
                    sum(1 for term in terms if term.lower() in lowered_text)
                )
            lowered_heading = heading.lower()
            if any(term.lower() in lowered_heading for term in terms):
                score *= HEADING_BOOST
            hits.append(
                SearchHit(
                    source=str(row['source']),
                    heading=heading,
                    start_line=int(row['start_line']),
                    end_line=int(row['end_line']),
                    text=text,
                    score=score,
                )
            )
        return hits

    def _search_fts(self, terms: Sequence[str], limit: int) -> list[SearchHit]:
        query = ' AND '.join(_quote_fts_term(term) for term in terms)
        rows = self._connection.execute(
            """
            SELECT text, source, heading, start_line, end_line, bm25(chunks) AS score
            FROM chunks
            WHERE chunks MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (query, limit * 4),
        ).fetchall()
        return self._rows_to_hits(rows, terms, use_bm25=True)

    def _search_like(self, terms: Sequence[str], limit: int) -> list[SearchHit]:
        clauses = ' OR '.join('text LIKE ? OR heading LIKE ?' for _ in terms)
        parameters: list[str] = []
        for term in terms:
            parameters.extend([f'%{term}%', f'%{term}%'])
        rows = self._connection.execute(
            f"""
            SELECT text, source, heading, start_line, end_line, 0.0 AS score
            FROM chunks
            WHERE {clauses}
            LIMIT ?
            """,
            (*parameters, limit * 4),
        ).fetchall()
        return self._rows_to_hits(rows, terms, use_bm25=False)

    @staticmethod
    def _drop_overlaps(hits: Sequence[SearchHit]) -> list[SearchHit]:
        """丢掉与已保留结果行号重叠的块，避免同一段话占满 top-k。"""
        kept: list[SearchHit] = []
        for hit in hits:
            overlaps = any(
                other.source == hit.source
                and hit.start_line <= other.end_line
                and other.start_line <= hit.end_line
                for other in kept
            )
            if not overlaps:
                kept.append(hit)
        return kept

    def search(self, query: str, *, limit: int = 3) -> tuple[SearchHit, ...]:
        """检索最相关的若干块，按分数从高到低返回。"""
        if limit < 1:
            raise ValueError('limit must be at least 1')
        terms = split_terms(query)
        if not terms:
            raise ValueError('query must not be empty')

        long_terms = [term for term in terms if len(term) >= MIN_TRIGRAM_CHARS]
        hits: list[SearchHit] = []
        if long_terms:
            hits = self._search_fts(long_terms, limit)
        if not hits:
            hits = self._search_like(terms, limit)

        ranked = sorted(hits, key=lambda hit: hit.score, reverse=True)
        return tuple(self._drop_overlaps(ranked)[:limit])


def format_hits(hits: Sequence[SearchHit], *, max_chars: int = 400) -> str:
    """把检索结果拼成带引用的上下文文本。"""
    if not hits:
        return '（未检索到相关内容）'
    blocks: list[str] = []
    for index, hit in enumerate(hits, start=1):
        body = hit.text if len(hit.text) <= max_chars else hit.text[:max_chars] + '...'
        blocks.append(f'[{index}] {hit.citation()}（{hit.heading}）\n{body}')
    return '\n\n'.join(blocks)