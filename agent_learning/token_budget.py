"""Token budget accounting and priority-based context assembly.

Agent 的上下文窗口是有限资源：系统提示、历史摘要、检索片段、最近对话、
工具输出都在争抢同一份预算。本模块提供三件事：

1. 不依赖 tokenizer 的中英混排 token 估算（estimate_tokens）；
2. 按优先级裁剪的分层预算规划（plan_context）；
3. 按 token 预算切分历史，供滚动摘要使用（split_for_summary）。

计费级精度请以 API 返回的 usage 为准；本模块用于本地预算决策与测试。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Literal, Sequence


CJK_RANGES: tuple[tuple[int, int], ...] = (
    (0x3000, 0x303F),  # CJK 标点
    (0x3040, 0x30FF),  # 日文假名
    (0x3400, 0x4DBF),  # 扩展 A
    (0x4E00, 0x9FFF),  # 基本汉字
    (0xF900, 0xFAFF),  # 兼容汉字
    (0xFF00, 0xFFEF),  # 全角字符
)

ASCII_CHARS_PER_TOKEN = 4
MESSAGE_OVERHEAD_TOKENS = 4
TRUNCATION_MARKER = '...[已截断]'
DROP_FROM_HEAD = 'head'
DROP_FROM_TAIL = 'tail'


def is_cjk(char: str) -> bool:
    """Return True when the character is CJK (about one token per character)."""
    if not char:
        return False
    code = ord(char[0])
    return any(start <= code <= end for start, end in CJK_RANGES)


def estimate_tokens(text: str) -> int:
    """Estimate tokens for mixed CJK/ASCII text without a tokenizer.

    汉字/全角字符按 1 token 计，其余字符按 4 字符 1 token 计。
    估算偏保守（宁多不少），用于本地预算决策。
    """
    if not text:
        return 0
    cjk = 0
    other = 0
    for char in text:
        if is_cjk(char):
            cjk += 1
        else:
            other += 1
    ascii_tokens = math.ceil(other / ASCII_CHARS_PER_TOKEN) if other else 0
    return cjk + ascii_tokens


def estimate_message_tokens(messages: Sequence[dict[str, Any]]) -> int:
    """Estimate tokens for a chat message list, including per-message overhead."""
    total = 0
    for message in messages:
        content = message.get('content')
        total += estimate_tokens(str(message.get('role', '')))
        total += estimate_tokens(content if isinstance(content, str) else '')
        total += MESSAGE_OVERHEAD_TOKENS
    return total


def truncate_to_tokens(text: str, limit: int) -> str:
    """Truncate text so its estimated token count stays within ``limit``.

    预算小到装不下截断标记时返回空串，避免"截断后反而超预算"。
    """
    if limit < 0:
        raise ValueError('limit must not be negative')
    if limit == 0:
        return ''
    if estimate_tokens(text) <= limit:
        return text

    marker_tokens = estimate_tokens(TRUNCATION_MARKER)
    if marker_tokens > limit:
        return ''

    low, high = 0, len(text)
    best = 0
    while low <= high:
        middle = (low + high) // 2
        if estimate_tokens(text[:middle]) + marker_tokens <= limit:
            best = middle
            low = middle + 1
        else:
            high = middle - 1
    return text[:best] + TRUNCATION_MARKER


@dataclass(frozen=True)
class ContextLayer:
    """A named slice of the prompt competing for the same token budget.

    priority 越小越先保留；drop_from 决定从哪一端丢弃片段：
    'tail' 适合按相关度排序的检索结果，'head' 适合按时间排序的历史消息。
    mandatory 层永不裁剪，超预算时通过报告暴露。
    """

    name: str
    priority: int
    segments: Sequence[str]
    drop_from: Literal['head', 'tail'] = DROP_FROM_TAIL
    mandatory: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError('layer name must not be empty')
        if self.drop_from not in (DROP_FROM_HEAD, DROP_FROM_TAIL):
            raise ValueError("drop_from must be 'head' or 'tail'")
        if isinstance(self.segments, str):
            raise TypeError('segments must be a sequence of strings, not a string')
        for segment in self.segments:
            if not isinstance(segment, str):
                raise TypeError('every segment must be a string')
        object.__setattr__(self, 'segments', tuple(self.segments))


@dataclass(frozen=True)
class LayerResult:
    """Outcome of budget planning for one layer."""

    name: str
    priority: int
    mandatory: bool
    requested_segments: int
    kept_segments: int
    requested_tokens: int
    kept_tokens: int

    @property
    def dropped_segments(self) -> int:
        return self.requested_segments - self.kept_segments

    @property
    def trimmed(self) -> bool:
        return self.dropped_segments > 0


@dataclass(frozen=True)
class BudgetReport:
    """Token accounting for one assembled prompt."""

    budget_tokens: int
    reserve_output_tokens: int
    layers: tuple[LayerResult, ...]

    @property
    def usable_tokens(self) -> int:
        return self.budget_tokens - self.reserve_output_tokens

    @property
    def requested_tokens(self) -> int:
        return sum(layer.requested_tokens for layer in self.layers)

    @property
    def total_tokens(self) -> int:
        return sum(layer.kept_tokens for layer in self.layers)

    @property
    def overflow_tokens(self) -> int:
        return max(0, self.total_tokens - self.usable_tokens)

    @property
    def utilization(self) -> float:
        if self.usable_tokens <= 0:
            return 0.0 if self.total_tokens == 0 else 1.0
        return self.total_tokens / self.usable_tokens

    @property
    def trimmed(self) -> bool:
        return any(layer.trimmed for layer in self.layers)

    def summary(self) -> str:
        """Return a one-line report suitable for logs."""
        parts = [
            f'{layer.name}={layer.kept_tokens}/{layer.requested_tokens}'
            for layer in self.layers
        ]
        return (
            f'tokens={self.total_tokens}/{self.usable_tokens} '
            f'overflow={self.overflow_tokens} ' + ' '.join(parts)
        )


@dataclass(frozen=True)
class BudgetPlan:
    """Kept segments per layer plus the accounting report."""

    report: BudgetReport
    segments: tuple[tuple[str, ...], ...]

    def render(self, separator: str = '\n\n') -> str:
        """Join kept segments, skipping layers that were fully dropped."""
        blocks = [separator.join(kept) for kept in self.segments if kept]
        return separator.join(blocks)


def _tokens_of(segments: Sequence[str]) -> int:
    return sum(estimate_tokens(segment) for segment in segments)


def plan_context(
    layers: Sequence[ContextLayer],
    budget_tokens: int,
    *,
    reserve_output_tokens: int = 0,
) -> BudgetPlan:
    """Fit layers into the budget by dropping the lowest priority segments.

    裁剪顺序：priority 从大到小（低优先级先丢），mandatory 层跳过。
    priority 相同时按传入顺序裁剪。
    """
    if budget_tokens < 1:
        raise ValueError('budget_tokens must be at least 1')
    if reserve_output_tokens < 0:
        raise ValueError('reserve_output_tokens must not be negative')
    if reserve_output_tokens > budget_tokens:
        raise ValueError('reserve_output_tokens must not exceed budget_tokens')

    names = [layer.name for layer in layers]
    if len(set(names)) != len(names):
        raise ValueError('layer names must be unique')

    usable = budget_tokens - reserve_output_tokens
    kept: list[list[str]] = [list(layer.segments) for layer in layers]
    total = sum(_tokens_of(segments) for segments in kept)

    trim_order = sorted(
        (index for index, layer in enumerate(layers) if not layer.mandatory),
        key=lambda index: layers[index].priority,
        reverse=True,
    )
    for index in trim_order:
        if total <= usable:
            break
        layer = layers[index]
        segments = kept[index]
        while total > usable and segments:
            dropped = segments.pop(0 if layer.drop_from == DROP_FROM_HEAD else -1)
            total -= estimate_tokens(dropped)

    results = tuple(
        LayerResult(
            name=layer.name,
            priority=layer.priority,
            mandatory=layer.mandatory,
            requested_segments=len(layer.segments),
            kept_segments=len(kept[index]),
            requested_tokens=_tokens_of(layer.segments),
            kept_tokens=_tokens_of(kept[index]),
        )
        for index, layer in enumerate(layers)
    )
    report = BudgetReport(
        budget_tokens=budget_tokens,
        reserve_output_tokens=reserve_output_tokens,
        layers=results,
    )
    return BudgetPlan(report=report, segments=tuple(tuple(s) for s in kept))


def split_for_summary(
    messages: Sequence[dict[str, Any]],
    keep_tokens: int,
    *,
    min_keep: int = 1,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split history into (to_summarize, to_keep) by tail token budget.

    从最新一条往前累计，直到再加一条就超出 keep_tokens；
    至少保留 min_keep 条，避免把正在进行的一轮对话摘要掉。
    """
    if keep_tokens < 0:
        raise ValueError('keep_tokens must not be negative')
    if min_keep < 1:
        raise ValueError('min_keep must be at least 1')

    items = list(messages)
    if not items:
        return [], []

    keep_count = 0
    used = 0
    for message in reversed(items):
        cost = estimate_message_tokens([message])
        if keep_count >= min_keep and used + cost > keep_tokens:
            break
        used += cost
        keep_count += 1

    if keep_count >= len(items):
        return [], items
    split = len(items) - keep_count
    return items[:split], items[split:]