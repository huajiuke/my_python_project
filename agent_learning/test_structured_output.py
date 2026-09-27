"""Tests for structured output extraction, validation and repair retries."""

import unittest
from typing import Any

from pydantic import Field

from agent_learning.structured_output import (
    JsonExtractionError,
    StrictModel,
    StructuredOutputError,
    ToolArgumentError,
    extract_json_object,
    schema_instruction,
    structured_call,
    to_tool_schema,
    validate_tool_arguments,
)


class NoteCard(StrictModel):
    """Small schema used by the tests."""

    title: str
    confidence: float = Field(ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)


class ScriptedLLM:
    """Return queued responses and record every call."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[list[dict[str, Any]], list[dict[str, Any]]]] = []

    def decide(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self.calls.append((messages, tools))
        if not self.responses:
            raise AssertionError('ScriptedLLM ran out of responses')
        return {'role': 'assistant', 'content': self.responses.pop(0)}

    def joined_messages(self, index: int) -> str:
        messages, _ = self.calls[index]
        return '\n'.join(str(message.get('content', '')) for message in messages)


def ask(card_text: str) -> list[dict[str, Any]]:
    return [{'role': 'user', 'content': card_text}]


class ExtractJsonObjectTest(unittest.TestCase):
    def test_returns_plain_object(self) -> None:
        self.assertEqual(extract_json_object('{"a": 1}'), '{"a": 1}')

    def test_strips_markdown_code_fence(self) -> None:
        text = '```json\n{"a": 1}\n```'
        self.assertEqual(extract_json_object(text), '{"a": 1}')

    def test_ignores_surrounding_prose(self) -> None:
        text = '好的，结果如下：\n{"a": {"b": 2}}\n以上。'
        self.assertEqual(extract_json_object(text), '{"a": {"b": 2}}')

    def test_keeps_braces_inside_strings(self) -> None:
        text = '{"text": "含有 { 和 } 的说明"}'
        self.assertEqual(extract_json_object(text), text)

    def test_keeps_escaped_quotes_inside_strings(self) -> None:
        text = '{"text": "他说 \\"你好\\" 了"}'
        self.assertEqual(extract_json_object(text), text)

    def test_returns_first_complete_object(self) -> None:
        self.assertEqual(extract_json_object('{"a": 1} 以及 {"b": 2}'), '{"a": 1}')

    def test_rejects_empty_output(self) -> None:
        with self.assertRaises(JsonExtractionError):
            extract_json_object('   ')

    def test_rejects_output_without_object(self) -> None:
        with self.assertRaises(JsonExtractionError):
            extract_json_object('这里没有 JSON')

    def test_rejects_unterminated_object(self) -> None:
        with self.assertRaises(JsonExtractionError):
            extract_json_object('{"a": 1')


class SchemaInstructionTest(unittest.TestCase):
    def test_lists_schema_fields(self) -> None:
        instruction = schema_instruction(NoteCard)
        self.assertIn('JSON Schema', instruction)
        self.assertIn('"title"', instruction)
        self.assertIn('"confidence"', instruction)

    def test_appends_hint(self) -> None:
        instruction = schema_instruction(NoteCard, hint='tags 用中文')
        self.assertTrue(instruction.endswith('tags 用中文'))


class StructuredCallTest(unittest.TestCase):
    def test_returns_validated_value_on_first_attempt(self) -> None:
        llm = ScriptedLLM(['{"title": "摘要", "confidence": 0.8}'])

        response = structured_call(llm, NoteCard, ask('生成卡片'))

        self.assertEqual(response.attempts, 1)
        self.assertEqual(response.value.title, '摘要')
        self.assertEqual(response.value.tags, [])

    def test_sends_schema_to_the_model(self) -> None:
        llm = ScriptedLLM(['{"title": "摘要", "confidence": 0.8}'])

        structured_call(llm, NoteCard, ask('生成卡片'))

        self.assertIn('JSON Schema', llm.joined_messages(0))

    def test_repairs_after_validation_failure(self) -> None:
        llm = ScriptedLLM(
            [
                '{"title": "摘要"}',
                '{"title": "摘要", "confidence": 0.5}',
            ]
        )

        response = structured_call(llm, NoteCard, ask('生成卡片'))

        self.assertEqual(response.attempts, 2)
        self.assertEqual(len(response.raw_outputs), 2)
        self.assertIn('confidence', llm.joined_messages(1))
        self.assertIn('上一次输出', llm.joined_messages(1))

    def test_repairs_after_unparsable_output(self) -> None:
        llm = ScriptedLLM(
            ['我不太确定', '{"title": "摘要", "confidence": 0.5}']
        )

        response = structured_call(llm, NoteCard, ask('生成卡片'))

        self.assertEqual(response.attempts, 2)
        self.assertIn('no JSON object', llm.joined_messages(1))

    def test_repairs_after_empty_output(self) -> None:
        llm = ScriptedLLM(['', '{"title": "摘要", "confidence": 0.5}'])

        response = structured_call(llm, NoteCard, ask('生成卡片'))

        self.assertEqual(response.attempts, 2)

    def test_rejects_unknown_fields(self) -> None:
        llm = ScriptedLLM(
            [
                '{"title": "摘要", "confidence": 0.5, "mood": "开心"}',
                '{"title": "摘要", "confidence": 0.5}',
            ]
        )

        response = structured_call(llm, NoteCard, ask('生成卡片'))

        self.assertEqual(response.attempts, 2)
        self.assertIn('mood', llm.joined_messages(1))

    def test_raises_after_exhausting_attempts(self) -> None:
        llm = ScriptedLLM(['{}', '{}', '{}'])

        with self.assertRaises(StructuredOutputError) as caught:
            structured_call(llm, NoteCard, ask('生成卡片'), max_attempts=3)

        error = caught.exception
        self.assertEqual(error.attempts, 3)
        self.assertEqual(len(error.raw_outputs), 3)
        self.assertIn('confidence', error.issue_text())
        self.assertEqual(len(llm.calls), 3)

    def test_rejects_attempt_limit_below_one(self) -> None:
        llm = ScriptedLLM(['{}'])

        with self.assertRaises(ValueError):
            structured_call(llm, NoteCard, ask('生成卡片'), max_attempts=0)


class ToToolSchemaTest(unittest.TestCase):
    def test_builds_function_schema(self) -> None:
        schema = to_tool_schema('save_card', '保存卡片', NoteCard)

        self.assertEqual(schema['type'], 'function')
        self.assertEqual(schema['function']['name'], 'save_card')
        self.assertEqual(schema['function']['description'], '保存卡片')
        self.assertIn('title', schema['function']['parameters']['properties'])

    def test_rejects_empty_name(self) -> None:
        with self.assertRaises(ValueError):
            to_tool_schema('  ', '保存卡片', NoteCard)


class ValidateToolArgumentsTest(unittest.TestCase):
    def test_accepts_json_string(self) -> None:
        card = validate_tool_arguments(
            NoteCard, '{"title": "摘要", "confidence": 0.5}'
        )

        self.assertEqual(card.title, '摘要')
        self.assertEqual(card.tags, [])

    def test_accepts_dict(self) -> None:
        card = validate_tool_arguments(NoteCard, {'title': '摘要', 'confidence': 0.5})

        self.assertEqual(card.confidence, 0.5)

    def test_rejects_invalid_json(self) -> None:
        with self.assertRaises(ToolArgumentError) as caught:
            validate_tool_arguments(NoteCard, '{"title": ')

        self.assertIn('不是合法 JSON', str(caught.exception))

    def test_rejects_wrong_field_type(self) -> None:
        with self.assertRaises(ToolArgumentError) as caught:
            validate_tool_arguments(
                NoteCard, '{"title": "摘要", "confidence": "high"}'
            )

        self.assertIn('confidence', str(caught.exception))

    def test_rejects_unknown_field(self) -> None:
        with self.assertRaises(ToolArgumentError) as caught:
            validate_tool_arguments(
                NoteCard, '{"title": "摘要", "confidence": 0.5, "mood": "开心"}'
            )

        self.assertIn('mood', str(caught.exception))

    def test_rejects_non_object_payload(self) -> None:
        with self.assertRaises(ToolArgumentError):
            validate_tool_arguments(NoteCard, '[1, 2, 3]')

    def test_rejects_unsupported_argument_type(self) -> None:
        with self.assertRaises(ToolArgumentError):
            validate_tool_arguments(NoteCard, 42)  # type: ignore[arg-type]


if __name__ == '__main__':
    unittest.main()