 # Agent 应用开发学习计划

 > 背景：已有 Python 后端基础（FastAPI、SQLAlchemy、MySQL），现在转向 Agent 应用开发
 > 目标：能独立完成"LLM + 工具 + RAG"的 Agent 应用，并具备生产化意识
 > 原则：先手写理解原理，再使用框架提升效率

 ---

 ## 一、学习链路总览

 | 阶段 | 内容 | 核心产出 | 预计时长 |
 |------|------|----------|----------|
 | 0 | FastAPI + 异步补强 | 已有项目包一层 REST API | 1-2 周 |
 | 1 | LLM API 工程 | CLI 智能助手 | 1 周 |
 | 2 | RAG 完整链路 | 个人知识库问答 | 2 周 |
 | 3 | 从零手写 Agent | Tool Calling Agent | 2 周 |
 | 4 | 框架化 | LangGraph Agent | 2-3 周 |
 | 5 | 生产化 | Agent API 服务 | 2-3 周 |
 | 6 | 多 Agent 与评测 | 复杂 Agent 应用 | 长期 |

 ---

 ## 二、各阶段明细

 ### 阶段 0：FastAPI + 异步补强（1-2 周）

 目标：Agent 应用需要流式输出和并发工具调用，先补齐异步服务端基础。

 - `asyncio` / `async/await`，理解并发与并行的区别
 - httpx 异步客户端
 - FastAPI `StreamingResponse` 实现 token 流式输出
 - Pydantic 校验、依赖注入、中间件

 项目：给 `fastApiProject` 增加一个聊天接口，支持流式返回。

 ### 阶段 1：LLM API 工程（1 周）

 目标：能独立调用 LLM API，处理输入输出和成本。

 - Chat Completions / Responses API 基础
 - System Prompt、Few-shot、角色设计
 - JSON 结构化输出、temperature、max_tokens
 - 流式输出、token 用量统计
 - Embedding 概念

 项目：CLI 智能助手，支持普通问答、结构化 JSON 输出、流式输出。

 ### 阶段 2：RAG 完整链路（2 周）

 目标：掌握"文档 -> 切分 -> 向量化 -> 检索 -> 生成"全流程。

 - 文档加载与切分策略
 - Embedding 模型选型
 - 向量库：Chroma 练手，Qdrant / pgvector / Milvus 了解
 - Top-K、相似度阈值、混合检索、重排序
 - 查询改写、多轮 RAG

 项目：把 `docs/` 和 `obsidian/` 学习笔记做成知识库问答工具。

 ### 阶段 3：从零手写 Agent（2 周）

 目标：不依赖框架，手写 Tool Calling + ReAct 循环。

 - 工具 Schema 设计与注册
 - 工具调用执行与结果回填
 - ReAct：Thought / Action / Observation 循环
 - 最大步数、超时、重试、错误处理
 - 短期记忆（消息历史）

 项目：`agent_learning/` 中的 Tool Calling Agent，再扩展为"运维助手"：
 - 查询 MySQL 表结构（只读）
 - 读取文件
 - 调用天气 API

 ### 阶段 4：框架化（2-3 周）

 目标：用成熟框架提升工程效率，但保留手写时的底层理解。

 - LangGraph：StateGraph、节点、条件边、Checkpoint
 - Human-in-the-loop：关键操作前让用户确认
 - MCP：工具协议标准化
 - 对比 LangChain、OpenAI Agents SDK、CrewAI

 项目：把阶段 3 的 Agent 迁移到 LangGraph，增加确认后执行和断点恢复。

 ### 阶段 5：生产化（2-3 周）

 目标：把 Agent 从 demo 变成可部署服务。

 - FastAPI 发布 Agent API：鉴权、限流、流式
 - 日志与追踪：Langfuse / LangSmith / 自建 trace
 - 评测体系：任务成功率、工具调用准确率、LLM-as-judge
 - 安全：Prompt Injection、工具白名单、只读权限
 - Docker 部署

 项目：部署一个带日志、评估和权限控制的 Agent API。

 ### 阶段 6：多 Agent 与评测（长期）

 - Multi-Agent 编排模式
 - 复杂任务规划与自我反思
 - Agent 评测自动化
 - 成本优化：缓存、小模型分流、任务路由

 ---

 ## 三、面试能力对照

 | 面试问题 | 学完哪个阶段能答 |
 |----------|------------------|
 | 什么是 Agent？ | 阶段 3 |
 | ReAct 原理？ | 阶段 3 |
 | 工具调用怎么实现？ | 阶段 3 |
 | RAG 链路怎么搭？ | 阶段 2 |
 | 如何防幻觉、防死循环？ | 阶段 3、5 |
 | LangGraph 怎么设计状态？ | 阶段 4 |
 | Agent 上线要注意什么？ | 阶段 5 |
 | 多 Agent 优缺点？ | 阶段 6 |

 ---

 ## 四、当前工作区

 - `docs/knowledge_ai_agent.md`：Agent 概念与面试笔记
 - `obsidian/04-AI与职业/`：Obsidian 版知识卡片
 - `agent_learning/`：从零手写 Agent 实战项目
