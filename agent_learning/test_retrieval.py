"""Tests for markdown chunking, FTS5 indexing and provenance."""

import tempfile
import unittest
from pathlib import Path

from agent_learning.retrieval import (
    Chunk,
    NoteIndex,
    SearchHit,
    chunk_markdown,
    format_hits,
    split_terms,
)


NOTE_A = '\n'.join(
    [
        '# 上下文工程',
        '',
        '## 为什么需要 token 预算',
        '',
        '汉字按 1 token 计。',
        '',
        '## 分层裁剪',
        '',
        '按优先级从低到高丢弃。',
        '',
        '### 代码块保护',
        '',
        '```python',
        '# 这不是标题',
        'print("hi")',
        '```',
    ]
)


class ChunkMarkdownTest(unittest.TestCase):
    def test_builds_heading_breadcrumbs(self) -> None:
        chunks = chunk_markdown(NOTE_A, source='note.md')

        headings = [chunk.heading for chunk in chunks]
        self.assertIn('上下文工程', headings)
        self.assertIn('上下文工程 > 为什么需要 token 预算', headings)
        self.assertIn('上下文工程 > 分层裁剪 > 代码块保护', headings)

    def test_records_line_ranges(self) -> None:
        chunks = chunk_markdown(NOTE_A, source='note.md')
        by_heading = {chunk.heading: chunk for chunk in chunks}

        self.assertEqual(by_heading['上下文工程'].start_line, 1)
        self.assertEqual(by_heading['上下文工程 > 为什么需要 token 预算'].start_line, 3)
        self.assertEqual(by_heading['上下文工程 > 分层裁剪'].start_line, 7)
        self.assertEqual(
            by_heading['上下文工程 > 分层裁剪 > 代码块保护'].start_line, 11
        )

    def test_ignores_headings_inside_code_fence(self) -> None:
        chunks = chunk_markdown(NOTE_A, source='note.md')

        self.assertNotIn('这不是标题', [chunk.heading for chunk in chunks])
        fenced = [
            chunk for chunk in chunks if 'print("hi")' in chunk.text
        ]
        self.assertEqual(len(fenced), 1)
        self.assertIn('# 这不是标题', fenced[0].text)

    def test_splits_oversized_section_within_token_budget(self) -> None:
        lines = ['## 长小节', ''] + [f'这是第 {index} 行说明文字。' for index in range(60)]
        text = '\n'.join(lines)

        chunks = chunk_markdown(text, source='long.md', max_tokens=30)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(chunk.tokens <= 30 for chunk in chunks))
        self.assertEqual(chunks[0].heading, '长小节')

    def test_keeps_long_code_block_in_one_chunk(self) -> None:
        body = '\n'.join(f'print("line {index}")' for index in range(40))
        text = '## 代码\n\n```python\n' + body + '\n```\n'

        chunks = chunk_markdown(text, source='code.md', max_tokens=20)

        fenced = [chunk for chunk in chunks if '```' in chunk.text]
        self.assertEqual(len(fenced), 1)
        self.assertGreater(fenced[0].tokens, 20)

    def test_document_without_headings_becomes_one_chunk(self) -> None:
        chunks = chunk_markdown('只有正文，没有标题。', source='plain.md')

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].heading, '')
        self.assertEqual(chunks[0].start_line, 1)

    def test_empty_document_produces_no_chunks(self) -> None:
        self.assertEqual(chunk_markdown('', source='empty.md'), ())

    def test_rejects_invalid_token_budget(self) -> None:
        with self.assertRaises(ValueError):
            chunk_markdown('内容', max_tokens=0)

    def test_citation_uses_source_and_start_line(self) -> None:
        chunk = Chunk(
            source='a/b.md', heading='h', start_line=12, end_line=20, text='x'
        )

        self.assertEqual(chunk.citation(), 'a/b.md:12')


class SplitTermsTest(unittest.TestCase):
    def test_splits_on_whitespace(self) -> None:
        self.assertEqual(split_terms('  token  预算 '), ['token', '预算'])

    def test_returns_empty_for_blank_query(self) -> None:
        self.assertEqual(split_terms('   '), [])


class NoteIndexSearchTest(unittest.TestCase):
    def setUp(self) -> None:
        self.index = NoteIndex()
        self.index.index_text(NOTE_A, 'note-a.md')

    def tearDown(self) -> None:
        self.index.close()

    def test_indexes_expected_chunk_count(self) -> None:
        self.assertEqual(self.index.count(), 4)

    def test_finds_chinese_substring(self) -> None:
        hits = self.index.search('分层裁剪')

        self.assertTrue(hits)
        self.assertEqual(hits[0].source, 'note-a.md')
        self.assertEqual(hits[0].start_line, 7)

    def test_finds_english_term(self) -> None:
        hits = self.index.search('token')

        self.assertTrue(hits)
        self.assertIn('token', hits[0].text)

    def test_hit_carries_provenance(self) -> None:
        hits = self.index.search('token')
        hit = hits[0]

        self.assertEqual(hit.citation(), f'note-a.md:{hit.start_line}')
        self.assertEqual(hit.heading, '上下文工程 > 为什么需要 token 预算')
        self.assertGreaterEqual(hit.end_line, hit.start_line)

    def test_respects_limit(self) -> None:
        self.index.index_text(NOTE_A.replace('token', '预算'), 'note-b.md')

        hits = self.index.search('预算', limit=1)

        self.assertEqual(len(hits), 1)

    def test_falls_back_to_like_for_short_query(self) -> None:
        hits = self.index.search('裁剪')

        self.assertTrue(hits)
        self.assertEqual(hits[0].start_line, 7)

    def test_returns_empty_for_unknown_term(self) -> None:
        self.assertEqual(self.index.search('完全不存在的词汇'), ())

    def test_heading_match_outranks_body_match(self) -> None:
        note = '\n'.join(
            [
                '# 标题',
                '## 分层裁剪',
                '正文一。',
                '## 其他',
                '这里也提到分层裁剪的概念。',
            ]
        )
        index = NoteIndex()
        try:
            index.index_text(note, 'boost.md')
            hits = index.search('分层裁剪')
        finally:
            index.close()

        self.assertEqual(hits[0].heading, '标题 > 分层裁剪')

    def test_reindexing_same_source_replaces_chunks(self) -> None:
        before = self.index.count()
        self.index.index_text('## 新内容\n\n新的正文。', 'note-a.md')

        self.assertEqual(self.index.count(), before - 3)
        self.assertEqual(self.index.search('token'), ())

    def test_clear_removes_everything(self) -> None:
        self.index.clear()

        self.assertEqual(self.index.count(), 0)

    def test_rejects_invalid_query_and_limit(self) -> None:
        with self.assertRaises(ValueError):
            self.index.search('   ')
        with self.assertRaises(ValueError):
            self.index.search('token', limit=0)

    def test_drop_overlaps_keeps_first_of_overlapping_range(self) -> None:
        first = SearchHit('a.md', 'h', 1, 10, 'x', 2.0)
        overlapping = SearchHit('a.md', 'h', 5, 15, 'y', 1.0)
        other_source = SearchHit('b.md', 'h', 5, 15, 'z', 0.5)

        kept = NoteIndex._drop_overlaps([first, overlapping, other_source])

        self.assertEqual([hit.text for hit in kept], ['x', 'z'])


class NoteIndexFilesTest(unittest.TestCase):
    def test_index_file_uses_relative_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'note.md').write_text('## 缓存\n\n缓存命中率。', encoding='utf-8')
            index = NoteIndex()
            try:
                index.index_file(root / 'note.md', root=root)
                hits = index.search('缓存命中率')
            finally:
                index.close()

            self.assertEqual(hits[0].source, 'note.md')
            self.assertEqual(hits[0].start_line, 1)

    def test_index_root_walks_markdown_and_skips_other_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'a.md').write_text('## 甲\n\n甲的内容。', encoding='utf-8')
            nested = root / 'sub'
            nested.mkdir()
            (nested / 'b.md').write_text('## 乙\n\n乙的内容。', encoding='utf-8')
            (nested / 'c.txt').write_text('忽略', encoding='utf-8')
            skipped = root / '.obsidian'
            skipped.mkdir()
            (skipped / 'd.md').write_text('## 丙\n\n丙的内容。', encoding='utf-8')

            index = NoteIndex()
            try:
                total = index.index_root(root)
                hits = index.search('乙的内容')
            finally:
                index.close()

            self.assertEqual(total, 2)
            self.assertEqual(hits[0].source, 'sub/b.md')

    def test_index_file_rejects_missing_file(self) -> None:
        index = NoteIndex()
        try:
            with self.assertRaises(FileNotFoundError):
                index.index_file('C:/definitely/not/here.md')
        finally:
            index.close()


class FormatHitsTest(unittest.TestCase):
    def test_includes_citation_and_heading(self) -> None:
        hit = SearchHit('note.md', '标题 > 小节', 3, 6, '正文内容。', 1.0)

        rendered = format_hits([hit])

        self.assertIn('note.md:3', rendered)
        self.assertIn('标题 > 小节', rendered)
        self.assertIn('正文内容。', rendered)

    def test_handles_empty_result(self) -> None:
        self.assertEqual(format_hits([]), '（未检索到相关内容）')

    def test_truncates_long_text(self) -> None:
        hit = SearchHit('note.md', 'h', 1, 1, '很长的正文' * 50, 1.0)

        rendered = format_hits([hit], max_chars=20)

        self.assertIn('...', rendered)


if __name__ == '__main__':
    unittest.main()