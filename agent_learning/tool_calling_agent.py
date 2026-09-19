"""从零实现的 Tool Calling Agent（教学版）。

不依赖 LangChain 等框架，只用标准库讲清楚 Agent 循环：
1. 用户输入进入消息列表
2. LLM 根据消息 + 工具 Schema 决定直接回答或调用工具
3. 调用工具后把 Observation 回填
4. 循环直到得到最终答案，或达到最大步数
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Protocol


def load_dotenv(dotenv_path: Path | None = None) -> Path | None:
    """加载 .env 文件中的配置到当前进程环境变量。

    不依赖 python-dotenv，按简单 KEY=VALUE 格式解析：
    - 跳过空行和 # 开头的注释
    - 兼容 export KEY=VALUE 前缀
    - 兼容单引号或双引号包裹的值
    - 已存在的系统环境变量优先级更高，不会被 .env 覆盖
    """
    if dotenv_path is not None:
        candidates = (dotenv_path,)
    else:
        script_dir = Path(__file__).resolve().parent
        repo_root = script_dir.parent
        candidates = (
            Path.cwd() / ".env",
            script_dir / ".env",
            repo_root / ".env",
        )

    for candidate in candidates:
        if not candidate.is_file():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export ") :]
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'\"").strip()
            if key and key not in os.environ:
                os.environ[key] = value
        return candidate
    return None


# ---------- 1. 消息与工具定义 ----------

ToolHandler = Callable[..., str]


@dataclass
class Tool:
    """Describe a callable tool and its runtime safety policy."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler
    read_only: bool = True
    timeout_seconds: float | None = None
    max_attempts: int = 1

    def __post_init__(self) -> None:
        '''Reject invalid policies before the Agent starts running.'''
        if self.max_attempts < 1:
            raise ValueError('max_attempts must be at least 1')
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError('timeout_seconds must be positive or None')


class LLM(Protocol):
    """LLM 适配层：输入消息和工具列表，返回 assistant 消息。"""

    def decide(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        ...


# ---------- 2. 工具注册表 ----------


class ToolRegistry:
    def __init__(self, allow_write_tools: bool = False) -> None:
        # Write tools are opt-in because the model must not mutate state by default.
        self._tools: dict[str, Tool] = {}
        self.allow_write_tools = allow_write_tools

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def schemas(self) -> list[dict[str, Any]]:
        """生成 OpenAI 兼容的 tool schema，传给 LLM 决定是否调用。"""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def call(self, name: str, arguments: dict[str, Any]) -> str:
        """执行工具并返回字符串 Observation。

        错误也返回成 Observation，这样 LLM 能看到失败原因并自我纠正。
        """
        tool = self._tools.get(name)
        if tool is None:
            return json.dumps({"error": f"工具不存在: {name}"}, ensure_ascii=False)
        if not tool.read_only and not self.allow_write_tools:
            return json.dumps(
                {
                    "error": (
                        f"工具权限不足: {name} 是写操作，"
                        "当前 Registry 未允许写工具"
                    ),
                    "attempts": 0,
                },
                ensure_ascii=False,
            )

        last_error = ""
        for attempt in range(1, tool.max_attempts + 1):
            try:
                result = self._call_handler(tool, arguments)
                return json.dumps({"result": result}, ensure_ascii=False)
            except TypeError as exc:
                # 参数错误无法通过原样重试恢复，立即返回给 LLM 修正。
                return json.dumps(
                    {"error": f"参数错误: {exc}", "attempts": attempt},
                    ensure_ascii=False,
                )
            except FutureTimeoutError:
                last_error = (
                    f"执行超时: {name} 超过 {tool.timeout_seconds} 秒"
                )
            except Exception as exc:
                last_error = f"执行失败: {exc}"

            if attempt < tool.max_attempts:
                continue

        return json.dumps(
            {"error": last_error, "attempts": tool.max_attempts},
            ensure_ascii=False,
        )

    @staticmethod
    def _call_handler(tool: Tool, arguments: dict[str, Any]) -> str:
        """Execute a sync tool with an optional timeout guard.

        A Python thread cannot be force-killed safely, so a timed-out handler
        may continue briefly in the background. Production systems should use
        process isolation or a cancellation protocol for long-running work.
        """
        if tool.timeout_seconds is None:
            return tool.handler(**arguments)

        executor = ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix=f"tool-{tool.name}",
        )
        future = executor.submit(tool.handler, **arguments)
        try:
            return future.result(timeout=tool.timeout_seconds)
        except FutureTimeoutError:
            future.cancel()
            raise
        finally:
            executor.shutdown(wait=False)


# ---------- 3. Mock LLM ----------


@dataclass
class MockLLM:
    """脚本化 LLM：按预设顺序决定调用工具或给出最终回答。

    seen_messages / seen_tools 用于测试时验证 Agent 是否正确回填 Observation。
    """

    script: list[dict[str, Any]]
    _next: int = 0
    seen_messages: list[list[dict[str, Any]]] = field(default_factory=list)
    seen_tools: list[list[dict[str, Any]]] = field(default_factory=list)

    def decide(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        self.seen_messages.append(messages)
        self.seen_tools.append(tools)

        item = self.script[self._next % len(self.script)]
        self._next += 1

        if item["type"] == "final":
            return {"role": "assistant", "content": item["content"]}

        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": f"call_{self._next}",
                    "type": "function",
                    "function": {
                        "name": item["name"],
                        "arguments": item["arguments"],
                    },
                }
            ],
        }


# ---------- 3.5 真实 LLM（OpenAI Chat Completions 兼容） ----------


class OpenAICompatibleLLM:
    """真实 LLM 适配层，把 OpenAI Chat Completions 响应转成 Agent 内部消息。

    推荐使用 openai 官方 Python SDK；本类不在模块导入时强依赖它，
    只有真正切换到真实 LLM 时才检查依赖，方便纯 Mock 模式离线运行。

    环境变量：
    - OPENAI_API_KEY：必填
    - OPENAI_BASE_URL：可选，兼容服务地址（代理、国产模型等）
    - OPENAI_MODEL：可选，默认 gpt-4o-mini
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        load_dotenv()
        self._ensure_openai_package()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("缺少 OPENAI_API_KEY 环境变量")

        from openai import OpenAI

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=base_url or os.getenv("OPENAI_BASE_URL"),
        )
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"

    @staticmethod
    def _ensure_openai_package() -> None:
        """确认 openai 包可用，缺失时给出可直接执行的安装提示。"""
        if importlib.util.find_spec("openai") is None:
            raise RuntimeError(
                "缺少 openai 依赖，请先运行: python -m pip install openai"
            )

    @staticmethod
    def _messages_for_api(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """把 Agent 内部消息转成 OpenAI API 需要的格式。

        MockLLM 阶段为了直观，把 arguments 保存成了 dict；OpenAI API 要求
        arguments 是 JSON 字符串，因此发送前统一序列化。
        """
        normalized: list[dict[str, Any]] = []
        for message in messages:
            if not message.get("tool_calls"):
                normalized.append(message)
                continue

            api_message = dict(message)
            api_tool_calls = []
            for call in message["tool_calls"]:
                arguments = call["function"].get("arguments")
                if not isinstance(arguments, str):
                    arguments = json.dumps(arguments, ensure_ascii=False)
                api_call = dict(call)
                api_call["function"] = {
                    "name": call["function"]["name"],
                    "arguments": arguments,
                }
                api_tool_calls.append(api_call)
            api_message["tool_calls"] = api_tool_calls
            normalized.append(api_message)
        return normalized

    @staticmethod
    def _assistant_from_api(message: Any) -> dict[str, Any]:
        """把 OpenAI 返回的 assistant message 转成 Agent 内部消息。

        这里统一把 arguments 字符串解析成 dict，后续 Agent 执行工具时
        可以直接用 **arguments 调用 Python 函数。
        """
        tool_calls = getattr(message, "tool_calls", None) or []
        if not tool_calls:
            return {
                "role": "assistant",
                "content": getattr(message, "content", None),
            }

        parsed_calls = []
        for call in tool_calls:
            raw_arguments = call.function.arguments
            if isinstance(raw_arguments, str):
                try:
                    arguments = json.loads(raw_arguments)
                except json.JSONDecodeError:
                    arguments = {}
            else:
                arguments = raw_arguments

            parsed_calls.append(
                {
                    "id": call.id,
                    "type": getattr(call, "type", None) or "function",
                    "function": {
                        "name": call.function.name,
                        "arguments": arguments,
                    },
                }
            )
        return {
            "role": "assistant",
            "content": getattr(message, "content", None),
            "tool_calls": parsed_calls,
        }

    def decide(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """调用 Chat Completions API，并返回 Agent 能继续处理的消息。"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=self._messages_for_api(messages),
            tools=tools or None,
        )
        return self._assistant_from_api(response.choices[0].message)


# ---------- 4. Agent 循环 ----------


@dataclass
class Agent:
    llm: LLM
    tools: ToolRegistry
    system_prompt: str = "你是一个乐于助人的 AI 助手，需要时使用工具获取信息。"
    max_steps: int = 5
    verbose: bool = True

    def run(self, user_input: str) -> str:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input},
        ]

        for step in range(1, self.max_steps + 1):
            assistant_msg = self.llm.decide(messages, self.tools.schemas())

            if not assistant_msg.get("tool_calls"):
                if self.verbose:
                    print(f"[Agent] 第 {step} 步：LLM 给出最终回答")
                return assistant_msg["content"]

            messages.append(assistant_msg)
            for call in assistant_msg["tool_calls"]:
                name = call["function"]["name"]
                arguments = call["function"]["arguments"]
                if self.verbose:
                    print(
                        f"[Agent] 第 {step} 步：调用工具 {name} "
                        f"参数 {arguments}"
                    )

                observation = self.tools.call(name, arguments)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call["id"],
                        "content": observation,
                    }
                )
                if self.verbose:
                    print(f"[Agent] 工具返回: {observation}")

        if self.verbose:
            print(f"[Agent] 达到最大步数 {self.max_steps}，任务未完成")
        return f"已达到最大步数 {self.max_steps}，任务未完成，请补充信息后重试。"


# ---------- 5. 示例工具 ----------


def get_weather(city: str) -> str:
    """模拟天气查询，实际项目替换为真实 API。"""
    return f"{city} 天气：晴，28°C，适合出门。"


def get_current_time() -> str:
    """返回当前系统时间，格式化到秒。"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_server_status() -> str:
    """模拟查询服务器运行状态。

    实际项目中可替换为读取系统指标、调用监控 API 或查询状态服务；
    这里先返回固定结果，方便无外部依赖地验证 Agent 工具调用链路。
    """
    return "服务器状态：正常，CPU 25%，内存 60%"


def build_demo_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="get_weather",
            description="获取指定城市的当前天气",
            parameters={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名"},
                },
                "required": ["city"],
            },
            handler=get_weather,
        )
    )
    registry.register(
        Tool(
            name="get_current_time",
            description="获取当前系统时间",
            parameters={"type": "object", "properties": {}},
            handler=get_current_time,
        )
    )
    registry.register(
        Tool(
            name="get_server_status",
            description="获取当前服务器的运行状态",
            parameters={"type": "object", "properties": {}},
            handler=get_server_status,
        )
    )
    return registry


def main() -> None:
    registry = build_demo_registry()
    if "--real" in sys.argv[1:]:
        # 切换到真实 LLM：python agent_learning/tool_calling_agent.py --real
        llm = OpenAICompatibleLLM()
    else:
        # 默认离线演示，不需要 API key，适合理解 Agent 循环。
        script = [
            {"type": "tool_call", "name": "get_weather", "arguments": {"city": "北京"}},
            {"type": "final", "content": "北京今天晴，28°C，适合出门。"},
        ]
        llm = MockLLM(script)

    agent = Agent(llm=llm, tools=registry)
    answer = agent.run("你好")
    print(f"\n最终回答: {answer}")


if __name__ == "__main__":
    main()
