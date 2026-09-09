"""Tool Calling Agent 核心循环测试。"""

import unittest
import os
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from agent_learning.tool_calling_agent import (
    Agent,
    MockLLM,
    OpenAICompatibleLLM,
    build_demo_registry,
    load_dotenv,
)


DOTENV_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "dotenv"
    / "test.env"
)


class ToolRegistryTest(unittest.TestCase):
    def test_schemas_contain_function_metadata(self):
        registry = build_demo_registry()
        schemas = registry.schemas()
        self.assertEqual(len(schemas), 3)

        weather = schemas[0]["function"]
        self.assertEqual(weather["name"], "get_weather")
        self.assertIn("description", weather)
        self.assertIn("city", weather["parameters"]["properties"])

        schema_names = [schema["function"]["name"] for schema in schemas]
        self.assertIn("get_server_status", schema_names)

    def test_call_unknown_tool_returns_error_observation(self):
        registry = build_demo_registry()
        result = registry.call("not_exist", {})
        self.assertIn("工具不存在", result)

    def test_call_wrong_arguments_returns_error_observation(self):
        registry = build_demo_registry()
        result = registry.call("get_weather", {})
        self.assertIn("参数错误", result)

    def test_call_server_status_returns_observation(self):
        registry = build_demo_registry()
        result = registry.call("get_server_status", {})
        self.assertIn("服务器状态", result)
        self.assertIn("CPU", result)


class AgentLoopTest(unittest.TestCase):
    def test_direct_answer_without_tool(self):
        llm = MockLLM([{"type": "final", "content": "你好，我不用工具。"}])
        agent = Agent(llm=llm, tools=build_demo_registry(), verbose=False)

        self.assertEqual(agent.run("你好"), "你好，我不用工具。")
        self.assertEqual(len(llm.seen_tools[0]), 3)

    def test_tool_call_then_final_answer(self):
        llm = MockLLM(
            [
                {
                    "type": "tool_call",
                    "name": "get_weather",
                    "arguments": {"city": "北京"},
                },
                {"type": "final", "content": "北京今天晴，28°C。"},
            ]
        )
        agent = Agent(llm=llm, tools=build_demo_registry(), verbose=False)

        self.assertEqual(agent.run("北京天气怎么样？"), "北京今天晴，28°C。")

        second_turn = llm.seen_messages[1]
        roles = [m["role"] for m in second_turn]
        self.assertIn("tool", roles)
        observation = [m for m in second_turn if m["role"] == "tool"][0]
        self.assertIn("北京", observation["content"])

    def test_max_steps_stops_loop(self):
        llm = MockLLM(
            [{"type": "tool_call", "name": "get_current_time", "arguments": {}}]
        )
        agent = Agent(
            llm=llm,
            tools=build_demo_registry(),
            verbose=False,
            max_steps=3,
        )

        result = agent.run("现在几点？")
        self.assertIn("已达到最大步数 3", result)
        self.assertEqual(len(llm.seen_messages), 3)

    def test_unknown_tool_error_can_lead_to_final_answer(self):
        llm = MockLLM(
            [
                {"type": "tool_call", "name": "not_exist", "arguments": {}},
                {"type": "final", "content": "抱歉，这个工具不可用。"},
            ]
        )
        agent = Agent(llm=llm, tools=build_demo_registry(), verbose=False)

        self.assertEqual(agent.run("查一下"), "抱歉，这个工具不可用。")

        observation = [
            m for m in llm.seen_messages[1] if m["role"] == "tool"
        ][0]
        self.assertIn("工具不存在", observation["content"])

    def test_server_status_tool_call_then_final_answer(self):
        llm = MockLLM(
            [
                {
                    "type": "tool_call",
                    "name": "get_server_status",
                    "arguments": {},
                },
                {"type": "final", "content": "服务器运行正常，CPU 25%，内存 60%。"},
            ]
        )
        agent = Agent(llm=llm, tools=build_demo_registry(), verbose=False)

        self.assertEqual(
            agent.run("服务器状态怎么样？"),
            "服务器运行正常，CPU 25%，内存 60%。",
        )

        observation = [
            m for m in llm.seen_messages[1] if m["role"] == "tool"
        ][0]
        self.assertIn("服务器状态", observation["content"])


class OpenAICompatibleLLMTest(unittest.TestCase):
    def test_load_dotenv_sets_missing_values(self):
        with patch.dict(os.environ, {}, clear=True):
            load_dotenv(DOTENV_FIXTURE)
            self.assertEqual(os.environ["OPENAI_API_KEY"], "file-api-key")
            self.assertEqual(
                os.environ["OPENAI_BASE_URL"],
                "https://example.com/v1",
            )
            self.assertEqual(os.environ["OPENAI_MODEL"], "test-model")

    def test_load_dotenv_does_not_override_existing_env(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "shell-key"}, clear=True):
            load_dotenv(DOTENV_FIXTURE)
            self.assertEqual(os.environ["OPENAI_API_KEY"], "shell-key")
            self.assertEqual(
                os.environ["OPENAI_BASE_URL"],
                "https://example.com/v1",
            )

    def test_load_dotenv_returns_none_when_missing(self):
        with patch.dict(os.environ, {}, clear=True):
            missing = (
                Path(__file__).resolve().parent
                / "fixtures"
                / "dotenv"
                / "missing.env"
            )
            self.assertIsNone(load_dotenv(missing))

    def test_missing_package_gives_install_hint(self):
        with patch(
            "agent_learning.tool_calling_agent.importlib.util.find_spec",
            return_value=None,
        ):
            with self.assertRaisesRegex(RuntimeError, "pip install openai"):
                OpenAICompatibleLLM._ensure_openai_package()

    def test_assistant_from_api_parses_tool_arguments(self):
        tool_call = SimpleNamespace(
            id="call_1",
            type="function",
            function=SimpleNamespace(
                name="get_weather",
                arguments='{"city": "北京"}',
            ),
        )
        api_message = SimpleNamespace(content=None, tool_calls=[tool_call])

        result = OpenAICompatibleLLM._assistant_from_api(api_message)

        self.assertEqual(result["role"], "assistant")
        self.assertEqual(
            result["tool_calls"][0]["function"]["arguments"],
            {"city": "北京"},
        )

    def test_assistant_from_api_keeps_direct_answer(self):
        api_message = SimpleNamespace(content="你好", tool_calls=None)

        result = OpenAICompatibleLLM._assistant_from_api(api_message)

        self.assertEqual(result["content"], "你好")
        self.assertNotIn("tool_calls", result)

    def test_messages_for_api_serializes_tool_arguments(self):
        internal_message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "get_weather",
                        "arguments": {"city": "北京"},
                    },
                }
            ],
        }

        normalized = OpenAICompatibleLLM._messages_for_api([internal_message])

        self.assertEqual(
            normalized[0]["tool_calls"][0]["function"]["arguments"],
            '{"city": "北京"}',
        )


if __name__ == "__main__":
    unittest.main()
