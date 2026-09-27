"""Structured LLM output: extraction, strict validation and repair retries.

自由文本适合聊天，不适合当接口。卡片、缺口、回检报告这类结果必须机器可读，
否则后面全是解析地狱。本模块提供四层防御：

1. schema 约束：把 JSON Schema 交给模型（schema_instruction）；
2. 提取：从带噪声的输出里取出第一个完整 JSON 对象（extract_json_object）；
3. 严格校验：Pydantic 严格模型，未知字段直接拒绝（StrictModel）；
4. 修复重试：把具体校验错误回喂给模型，重试仍失败就抛出，**绝不替模型猜**。

另外提供工具参数校验（validate_tool_arguments），
用于 function calling 的 arguments 字符串——执行前必须校验。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Generic, Protocol, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError


ModelT = TypeVar('ModelT', bound=BaseModel)


class StrictModel(BaseModel):
    """Base model for LLM output: unknown fields are rejected."""

    model_config = ConfigDict(extra='forbid')


class StructuredLLM(Protocol):
    """Minimal LLM interface required by structured_call."""

    def decide(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ...


class JsonExtractionError(ValueError):
    """Raised when no complete JSON object can be found."""


class ToolArgumentError(ValueError):
    """Raised when tool call arguments fail validation."""


class StructuredOutputError(RuntimeError):
    """Raised when the model never produced schema-valid output."""

    def __init__(
        self,
        message: str,
        *,
        issues: Sequence['ValidationIssue'] = (),
        attempts: int = 0,
        raw_outputs: Sequence[str] = (),
    ) -> None:
        super().__init__(message)
        self.issues = tuple(issues)
        self.attempts = attempts
        self.raw_outputs = tuple(raw_outputs)

    def issue_text(self) -> str:
        """Return all validation issues on one line, for logs."""
        return '; '.join(issue.text for issue in self.issues)


@dataclass(frozen=True)
class ValidationIssue:
    """One validation problem, located by a JSON path."""

    path: str
    message: str

    @property
    def text(self) -> str:
        return f'{self.path}: {self.message}'


@dataclass(frozen=True)
class StructuredResponse(Generic[ModelT]):
    """A validated model instance plus the cost of getting there."""

    value: ModelT
    attempts: int
    raw_outputs: tuple[str, ...]


def extract_json_object(text: str) -> str:
    """Return the first complete JSON object found in model output.

    容忍 Markdown 代码块、前后解释文字、对象内嵌套与字符串里的花括号。
    """
    if not isinstance(text, str) or not text.strip():
        raise JsonExtractionError('model output is empty')

    start = text.find('{')
    if start == -1:
        raise JsonExtractionError('no JSON object found in model output')

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    raise JsonExtractionError('unterminated JSON object in model output')


def issues_from_pydantic(error: ValidationError) -> tuple[ValidationIssue, ...]:
    """Convert a Pydantic ValidationError into flat, loggable issues."""
    issues: list[ValidationIssue] = []
    for item in error.errors():
        location = '.'.join(str(part) for part in item.get('loc', ())) or '<root>'
        issues.append(
            ValidationIssue(path=location, message=str(item.get('msg', 'invalid')))
        )
    return tuple(issues)


def schema_instruction(
    model_class: type[BaseModel],
    hint: str | None = None,
) -> str:
    """Build the instruction that hands the JSON Schema to the model."""
    schema = json.dumps(
        model_class.model_json_schema(), ensure_ascii=False, indent=2
    )
    parts = [
        '请只输出一个 JSON 对象，不要输出解释、Markdown 代码块或多余文字。',
        '字段必须严格符合下面的 JSON Schema，不要添加 Schema 之外的字段：',
        schema,
    ]
    if hint:
        parts.append(hint)
    return '\n'.join(parts)


def _repair_instruction(issues: Sequence[ValidationIssue], raw: str) -> str:
    lines = ['上一次输出没有通过校验，请只返回修正后的 JSON 对象。', '需要修正的问题：']
    lines.extend(f'- {issue.text}' for issue in issues)
    lines.append('上一次输出：')
    lines.append(raw if raw.strip() else '(空输出)')
    return '\n'.join(lines)


def _try_parse(
    raw: str,
    model_class: type[ModelT],
) -> tuple[ModelT | None, tuple[ValidationIssue, ...]]:
    """Return (instance, issues); exactly one of them is meaningful."""
    try:
        payload_text = extract_json_object(raw)
    except JsonExtractionError as exc:
        return None, (ValidationIssue(path='<output>', message=str(exc)),)

    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        return None, (
            ValidationIssue(
                path='<output>',
                message=f'JSON 解析失败: {exc.msg}（第 {exc.lineno} 行第 {exc.colno} 列）',
            ),
        )

    if not isinstance(payload, dict):
        return None, (ValidationIssue(path='<output>', message='顶层必须是 JSON 对象'),)

    try:
        return model_class.model_validate(payload), ()
    except ValidationError as exc:
        return None, issues_from_pydantic(exc)


def structured_call(
    llm: StructuredLLM,
    model_class: type[ModelT],
    messages: Sequence[dict[str, Any]],
    *,
    tools: Sequence[dict[str, Any]] = (),
    max_attempts: int = 3,
    schema_hint: str | None = None,
) -> StructuredResponse[ModelT]:
    """Ask the LLM for schema-valid output, repairing and retrying on failure.

    失败时把"具体哪个字段错了"回喂给模型，而不是笼统说"格式不对"。
    """
    if max_attempts < 1:
        raise ValueError('max_attempts must be at least 1')

    conversation = [dict(message) for message in messages]
    conversation.append(
        {'role': 'user', 'content': schema_instruction(model_class, schema_hint)}
    )

    raw_outputs: list[str] = []
    last_issues: tuple[ValidationIssue, ...] = ()

    for attempt in range(1, max_attempts + 1):
        response = llm.decide([dict(m) for m in conversation], list(tools))
        content = response.get('content') if isinstance(response, dict) else None
        raw = content if isinstance(content, str) else ''
        raw_outputs.append(raw)

        value, issues = _try_parse(raw, model_class)
        if value is not None:
            return StructuredResponse(
                value=value, attempts=attempt, raw_outputs=tuple(raw_outputs)
            )

        last_issues = issues
        if attempt < max_attempts:
            conversation.append({'role': 'assistant', 'content': raw})
            conversation.append(
                {'role': 'user', 'content': _repair_instruction(issues, raw)}
            )

    raise StructuredOutputError(
        f'structured output failed after {max_attempts} attempt(s)',
        issues=last_issues,
        attempts=max_attempts,
        raw_outputs=tuple(raw_outputs),
    )


def to_tool_schema(
    name: str,
    description: str,
    model_class: type[BaseModel],
) -> dict[str, Any]:
    """Build an OpenAI-style function schema from a Pydantic model."""
    if not name.strip():
        raise ValueError('tool name must not be empty')
    return {
        'type': 'function',
        'function': {
            'name': name,
            'description': description,
            'parameters': model_class.model_json_schema(),
        },
    }


def validate_tool_arguments(
    model_class: type[ModelT],
    arguments: str | dict[str, Any],
) -> ModelT:
    """Validate raw function-call arguments before executing a tool.

    模型给出的 arguments 只是字符串，工具执行前必须校验——这是权限之外的第二道闸门。
    """
    if isinstance(arguments, str):
        try:
            payload = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise ToolArgumentError(
                f'arguments 不是合法 JSON: {exc.msg}（第 {exc.lineno} 行第 {exc.colno} 列）'
            ) from exc
    elif isinstance(arguments, dict):
        payload = arguments
    else:
        raise ToolArgumentError('arguments 必须是 JSON 字符串或 dict')

    if not isinstance(payload, dict):
        raise ToolArgumentError('arguments 必须解析为 JSON 对象')

    try:
        return model_class.model_validate(payload)
    except ValidationError as exc:
        issues = issues_from_pydantic(exc)
        raise ToolArgumentError('; '.join(issue.text for issue in issues)) from exc