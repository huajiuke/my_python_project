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

 ## 扩展任务

 1. 增加 `get_current_time`、文件读取等工具，观察多工具如何选择
 2. 把 `MockLLM` 替换成 OpenAI 兼容 API 的真实 LLM 调用
 3. 给工具增加"只读 / 可写"权限，模拟生产环境权限控制
 4. 增加超时与重试，观察 LLM 如何从错误中恢复
