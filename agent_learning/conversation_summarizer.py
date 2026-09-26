"""LLM-based rolling summary for conversation history."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class SummaryLLM(Protocol):
    """Minimal LLM interface required by the summarizer."""

    def decide(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ...


@dataclass
class ConversationSummarizer:
    """Merge an existing summary and older messages into a compact summary."""

    llm: SummaryLLM
    max_summary_chars: int = 2000

    def __post_init__(self) -> None:
        if self.max_summary_chars < 1:
            raise ValueError('max_summary_chars must be at least 1')

    @staticmethod
    def _format_messages(messages: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for message in messages:
            role = str(message.get('role', 'unknown'))
            content = str(message.get('content', '')).strip()
            lines.append(f'{role}: {content}')
        return '\n'.join(lines)

    def summarize(
        self,
        previous_summary: str | None,
        messages: list[dict[str, Any]],
    ) -> str:
        """Return a bounded rolling summary for the supplied message window."""
        if not messages:
            raise ValueError('messages must not be empty')

        previous = previous_summary.strip() if previous_summary else '无'
        prompt = (
            '请把已有摘要和新增对话合并成一份滚动记忆。\n'
            '保留用户目标、确定事实、个人偏好、已完成事项、未解决问题和重要约束；'
            '删除寒暄、重复内容和无关细节。只输出摘要正文。\n\n'
            f'## 已有摘要\n{previous}\n\n'
            f'## 新增对话\n{self._format_messages(messages)}'
        )
        assistant_msg = self.llm.decide(
            [
                {
                    'role': 'system',
                    'content': '你是对话记忆压缩器，输出简洁、准确、可继续追问的中文摘要。',
                },
                {'role': 'user', 'content': prompt},
            ],
            [],
        )
        content = assistant_msg.get('content')
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError('summarizer returned an empty response')

        summary = content.strip()
        if len(summary) > self.max_summary_chars:
            marker = '...[摘要已截断]'
            if self.max_summary_chars <= len(marker):
                summary = summary[: self.max_summary_chars]
            else:
                summary = (
                    summary[: self.max_summary_chars - len(marker)]
                    + marker
                )
        return summary
