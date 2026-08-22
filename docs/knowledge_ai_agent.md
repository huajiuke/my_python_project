 # AI Agent 学习笔记（面试用）
 
 > 目的：面试了解层面，能讲清核心概念、主流架构和关键框架即可
 > 不需要手写 Agent 框架，重点在理解思路
 
 ---
 
 ## 一、什么是 AI Agent
 
 ### 定义
 
 **AI Agent（智能体）** 是一个能自主感知环境、做出推理决策并执行行动的 AI 系统。它不只是"问一句答一句"，而是有目标的、能持续行动的。
 
 ### Agent vs 普通 LLM 调用
 
 |  | 普通 LLM 调用 | AI Agent |
 |--|--|--|
 | 交互方式 | 单轮问答，用户每次输入，LLM 每次输出 | 多步执行，Agent 自主决定下一步做什么 |
 | 状态保持 | 无（或靠对话历史） | 有内部状态（记忆、进度、中间结果） |
 | 工具使用 | 不能主动调用外部工具 | 能调用 API、数据库、搜索引擎等工具 |
 | 目标导向 | 被动响应 | 主动规划，分解任务，朝目标前进 |
 | 错误处理 | 出错就得用户重新输入 | 能自我纠正、重试、回退 |
 
 **一句话概括**：LLM 是"大脑"，Agent 是"大脑 + 手 + 工具"。
 
 ### Agent 四大核心能力模块
 
 | 模块 | 说明 |
 |--|--|
 | **Planning** | 将大目标拆解为子任务，决定执行顺序 |
 | **Memory** | 短期记忆（当前对话上下文） + 长期记忆（向量数据库/知识库） |
 | **Tool Use** | 调用外部 API、执行代码、查询数据库等 |
 | **Execution** | 执行动作并观察结果，反馈到下一步决策 |
 
 ---
 
 ## 二、关键架构模式
 
 ### 1. ReAct（Reasoning + Acting）
 
 目前最主流的 Agent 模式，由 Google 在 2022 年提出。
 
 **工作流程**：
 
 ```
 Thought: 用户想查北京的天气，我需要查天气工具
 Action: 调用 get_weather(city="北京")
 Observation: {"temp": 28, "weather": "晴"}
 Thought: 拿到结果了，整理一下回复用户
 Final: 回复用户
 ```
 
 **面试回答要点**：
 - ReAct 把推理轨迹（Thought）和行动（Action）交织在一起
 - 解决了纯 CoT（思维链）无法获取外部信息的问题
 - 每次 Action 的输出作为 Observation 喂回模型，形成闭环
 
 ### 2. Function Calling / Tool Calling
 
 OpenAI 在 2023 年 6 月引入的功能，现已成为 Agent 的事实标准接口。
 
 **工作流程**：
 1. 开发者定义一组工具的 Schema（含参数描述）
 2. LLM 判断是否需要调用工具，返回结构化调用请求
 3. 开发者执行工具并返回结果
 4. LLM 结合工具结果生成最终回答
 
 **Function Calling vs Tool Calling**：本质上是一回事，OpenAI API 从 v1.1.0 开始用 `tools` 代替 `functions`，但概念相同。
 
 ### 3. Plan-and-Solve
 
 先规划再执行的两阶段模式：
 - **Plan**：LLM 先生成完整的执行计划（步骤列表）
 - **Solve**：按计划逐步执行，每步可能调用工具
 - 与 ReAct 的区别：ReAct 边想边做，Plan-and-Solve 想好再做
 
 **适用场景**：任务步骤明确、不适合频繁切换上下文的情况。
 
 ### 4. Multi-Agent 协作
 
 多个 Agent 各司其职，协同完成复杂任务。
 
 | 模式 | 说明 | 例子 |
 |--|--|--|
 | 主管-下属 | 一个协调 Agent 分配任务给子 Agent | AutoGPT |
 | 辩论式 | 多个 Agent 各自推理后讨论达成共识 | ChatDev |
 | 流水线式 | Agent 链式传递中间结果 | CrewAI 的 Sequential Process |
 
 **面试常问**：Multi-Agent 的优势和挑战？
 - 优势：分工明确、可并行、每个 Agent 的 prompt 更聚焦
 - 挑战：通信开销、协调复杂度、错误传播（一个 Agent 出错会影响下游）
 
 ---
 
 ## 三、RAG vs Agent
 
 | | RAG | Agent |
 |--|--|--|
 | 目的 | 让 LLM 获取外部知识，减少幻觉 | 让 LLM 自主完成任务 |
 | 核心能力 | 检索 + 生成 | 规划 + 工具调用 + 执行 |
 | 复杂度 | 相对简单，一次检索 + 一次生成 | 多步循环，可能有分支 |
 | 典型场景 | 客服问答、知识库查询 | 自动化操作、数据分析、代码生成 |
 
 **两者结合**：RAG 可以作为 Agent 的"长期记忆"模块。Agent 判断需要查找知识 → 调用 RAG 工具检索向量数据库 → 获取上下文 → 继续推理。
 
 ---
 
 ## 四、主流框架对比
 
 | 框架 | 定位 | 核心特点 | 适合谁 |
 |--|--|--|--|
 | **LangChain** | 全能型 Agent 框架 | 组件化设计，LCEL 表达式，生态最丰富 | 需要深度定制的开发者 |
 | **CrewAI** | Multi-Agent 框架 | 角色定义清晰，开箱即用 | 想快速搭建多 Agent 协作 |
 | **AutoGPT** | 自主 Agent | 全自动执行长期任务，但容易跑偏 | 实验性质，了解概念 |
 | **OpenAI Agents SDK** | 官方轻量框架 | 基于 OpenAI API，代码简洁 | 已有 OpenAI 调用的项目 |
 | **Dify** | 低代码 Agent 平台 | 可视化编排、拖拽式 | 非开发者或快速原型 |
 
 ### LangChain 核心组件（面试重点）
 
 ```
 Model I/O: LLM 调用封装
     ↓
 Retrieval: 文档加载、向量存储、检索
     ↓
 Chains: 串联多个调用（LLM + 工具）
     ↓
 Agents: Agent 类型 + Tool 定义 + AgentExecutor
     ↓
 Memory: 对话记忆管理
     ↓
 Callbacks: 日志、监控、流式输出
 ```
 
 **LangChain 面试常问**：
 - LCEL 是什么？答：声明式管道语法，用 `|` 连接组件，类似 Unix 管道
 - AgentExecutor 的作用？答：循环执行 Agent，处理工具调用和结果返回
 - Tool 和 Toolkits 的区别？答：Tool 是单个工具，Toolkits 是一组相关工具的集合
 
 ---
 
 ## 五、面试常考问题
 
 ### Q1: 什么是 AI Agent？和 LLM 有什么区别？
 
 思路：Agent = LLM + 规划 + 记忆 + 工具。LLM 只是"大脑"，Agent 是能自主行动的完整系统。用前面的对比表格回答即可。
 
 ### Q2: ReAct 模式的工作原理？
 
 思路：Thought → Action → Observation 循环。LLM 交替输出推理和行动指令，每次行动后观察结果反馈给下一步决策。Google 2022 年论文提出。
 
 ### Q3: Function Calling 怎么实现的？
 
 思路：定义工具 Schema → 传入 tools 参数 → LLM 返回结构化参数 → 执行工具 → 结果传回 LLM 生成回答。
 
 ### Q4: Agent 的幻觉问题怎么处理？
 
 思路：引入外部工具验证、RAG 提供真实上下文、多 Agent 交叉验证、关键操作让用户确认。
 
 ### Q5: Multi-Agent 的优缺点？
 
 思路：优势 — 分工明确、可并行、专注度高。挑战 — 通信开销大、协调复杂、错误传播、成本高。
 
 ### Q6: Agent 的记忆机制怎么设计？
 
 思路：短期记忆（对话历史）+ 长期记忆（向量数据库）+ 混合策略（最近 N 轮 + 检索相关内容）。
 
 ### Q7: LangChain 的核心组件？
 
 思路：Model I/O → Retrieval → Chains → Agents → Memory → Callbacks。重点说 Agents（Agent 类型 + Tool + AgentExecutor）和 Chains。
 
 ### Q8: 什么是 Tool Calling 中的 Tool Schema？
 
 思路：用 JSON Schema 描述工具的 name、description、parameters。Description 越清晰，LLM 调用越准确。
 
 ### Q9: RAG 和 Agent 的关系？
 
 思路：RAG 解决"知识不足"，Agent 解决"需要行动"。可以结合使用，不是替代关系。
 
 ### Q10: Agent 在什么场景下不合适？
 
 思路：简单问答（成本高）、需要确定性结果的场景、安全敏感操作、预算有限。
 
 ### Q11: 如何避免 Agent 陷入死循环？
 
 思路：设置 max_iterations、超时机制、阶段性结果检查、不确定时主动询问用户。
 
 ### Q12: 你用过哪些 Agent 框架？对比一下？
 
 思路：对比 LangChain（重生态）、CrewAI（多 Agent）、OpenAI Agents SDK（轻量官方），重点讲设计取舍。
 
 ---
 
 ## 六、Python 示例：Function Calling 实现简单 Agent
 
 用 OpenAI API 演示最核心的 Agent 循环逻辑（不依赖任何框架）：
 
 ```python
 import json
 from openai import OpenAI
 
 client = OpenAI()
 
 # 1. 定义工具
 tools = [
     {
         "type": "function",
         "function": {
             "name": "get_weather",
             "description": "获取指定城市的天气",
             "parameters": {
                 "type": "object",
                 "properties": {
                     "city": {"type": "string", "description": "城市名"}
                 },
                 "required": ["city"]
             }
         }
     }
 ]
 
 # 2. 工具实现
 def get_weather(city: str) -> str:
     return f"{city} 天气：晴，28°C"
 
 # 3. Agent 循环
 messages = [{"role": "user", "content": "北京今天天气怎么样？适合出门吗？"}]
 
 for _ in range(5):  # 最大 5 步
     response = client.chat.completions.create(
         model="gpt-4o",
         messages=messages,
         tools=tools,
     )
     msg = response.choices[0].message
 
     if msg.tool_calls:
         messages.append(msg)
         for tc in msg.tool_calls:
             if tc.function.name == "get_weather":
                 args = json.loads(tc.function.arguments)
                 result = get_weather(args["city"])
                 messages.append({
                     "role": "tool",
                     "tool_call_id": tc.id,
                     "content": result
                 })
     else:
         print(msg.content)
         break
 ```
 
 **关键逻辑**：
 1. 将 tools 定义传给 API
 2. 检查 response 中是否包含 `tool_calls`
 3. 有则执行工具 → 结果追加回 messages
 4. 无则输出最终回答 → 退出循环
 
 ---
 
 ## 七、面试知识地图
 
 ```
 1. 概念层 — 什么是 Agent、四大模块、Agent vs LLM
 2. 架构层 — ReAct、Function Calling、Plan-and-Solve、Multi-Agent
 3. 框架层 — LangChain、CrewAI、OpenAI Agents SDK、Dify
 4. 实践层 — RAG vs Agent、幻觉处理、死循环避免、记忆设计
 ```
