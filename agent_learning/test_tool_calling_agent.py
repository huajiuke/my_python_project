"""Tool Calling Agent 核心循环测试。"""

import unittest

from agent_learning.tool_calling_agent import (
    Agent,
    MockLLM,
    build_demo_registry,
)


class ToolRegistryTest(unittest.TestCase):
    def test_schemas_contain_function_metadata(self):
        registry = build_demo_registry()
        schemas = registry.schemas()
        self.assertEqual(len(schemas), 2)

        weather = schemas[0]["function"]
        self.assertEqual(weather["name"], "get_weather")
        self.assertIn("description", weather)
        self.assertIn("city", weather["parameters"]["properties"])

    def test_call_unknown_tool_returns_error_observation(self):
        registry = build_demo_registry()
        result = registry.call("not_exist", {})
        self.assertIn("工具不存在", result)

    def test_call_wrong_arguments_returns_error_observation(self):
        registry = build_demo_registry()
        result = registry.call("get_weather", {})
        self.assertIn("参数错误", result)


class AgentLoopTest(unittest.TestCase):
    def test_direct_answer_without_tool(self):
        llm = MockLLM([{"type": "final", "content": "你好，我不用工具。"}])
        agent = Agent(llm=llm, tools=build_demo_registry(), verbose=False)

        self.assertEqual(agent.run("你好"), "你好，我不用工具。")
        self.assertEqual(len(llm.seen_tools[0]), 2)

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


if __name__ == "__main__":
    unittest.main()
