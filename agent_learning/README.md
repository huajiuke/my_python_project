 # Agent 从零手写项目

 > 目标：不依赖 LangChain 等框架，用标准库写一遍 Tool Calling Agent，理解 Agent 最核心的循环。

 ## 核心循环

 ```
 用户输入
    ↓
 LLM 接收消息 + 工具列表
    ↓
 判断：直接回答？还是调用工具？
    ├─ 直接回答 → 结束
    └─ 调用工具 → 执行工具 → 结果回填消息 → 回到 LLM
 ```

 这就是 ReAct（Reasoning + Acting）的工程化形态：
 LLM 交替做"思考"和"行动"，每次行动后把 Observation 喂回去，直到给出最终答案。

 ## 文件结构

 ```text
 agent_learning/
 ├── README.md                  # 项目说明
 ├── tool_calling_agent.py      # 从零实现：Tool + Registry + MockLLM + Agent
 └── test_tool_calling_agent.py # 单元测试，覆盖核心循环
 ```

 ## 运行

 无需安装任何依赖，直接用 Python 运行：

 ```powershell
 python agent_learning/tool_calling_agent.py
 ```

运行单元测试：

 ```powershell
 python -m unittest discover -s agent_learning -v
 ```

 ## 切换到真实 LLM

 Agent 循环已经接好 OpenAI Chat Completions 兼容接口，先安装官方 SDK：

 ```powershell
 python -m pip install openai
 ```

 配置环境变量：

 ```powershell
 $env:OPENAI_API_KEY = "你的 API Key"
 $env:OPENAI_BASE_URL = "可选：兼容服务地址"
 $env:OPENAI_MODEL = "可选：默认 gpt-4o-mini"
 ```

 用真实模型运行：

```powershell
python agent_learning/tool_calling_agent.py --real
```

观察真实模型返回的工具参数如何在 JSON 字符串和 Python dict 之间转换：

```powershell
python agent_learning/tool_calling_agent.py --real --debug-tool-arguments
```

也可以直接传入问题，观察模型如何在多个工具中选择：

```powershell
python agent_learning/tool_calling_agent.py --real "现在几点？"
python agent_learning/tool_calling_agent.py --real "读取 docs/knowledge_ai_agent.md 的前 500 个字符"
```

输出结构化 JSON 事件，用于查看每一步的模型决策、工具状态和耗时：

```powershell
python agent_learning/tool_calling_agent.py --trace-logs
```

 没有配置 API Key 时仍可运行默认的 Mock 演示，方便先理解循环本身。

## 工具运行策略

- `read_only=True` 是默认值，适合查询类工具。
- `read_only=False` 的写工具默认会被 `ToolRegistry` 拦截，只有显式设置 `allow_write_tools=True` 才允许执行。
- `timeout_seconds` 控制单次执行的等待时间，超时会作为 Observation 返回给 LLM。
- `max_attempts` 控制最多执行次数，普通异常会重试，参数错误不会做无意义重试。

## 扩展任务

1. 已完成：增加 `get_current_time` 和受限文件读取工具，支持多工具选择
2. 已完成：通过 `--debug-tool-arguments` 观察 `tool_calls.arguments` 的 JSON 字符串到 dict 转换
3. 已完成：工具支持只读 / 可写权限，默认阻止写操作
4. 已完成：工具支持超时与重试，错误会回填给 LLM
5. 已完成：结构化日志记录 Agent、LLM、工具调用、状态和耗时，并自动脱敏
6. 为工具调用增加请求级权限上下文，而不是只使用全局开关
