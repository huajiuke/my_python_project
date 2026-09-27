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
├── token_budget.py            # token 估算、分层预算裁剪、按 token 切分历史
├── structured_output.py       # 结构化输出：提取 + 严格校验 + 修复重试
├── retrieval.py               # 检索：Markdown 切块 + FTS5 索引 + 段落级溯源
├── eval_harness.py            # 评估：用例集 + 基线报告 + 回归对比
├── note_qa_agent.py           # 汇合点：检索 + token 预算 + 结构化回答
├── note_qa_eval.py            # NoteQAAgent 的用例集与基线回归
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

每次运行可以单独限制工具白名单和写权限：

```python
context = RunContext(
    allowed_tools=frozenset({"get_current_time", "read_text_file"}),
    allow_write_tools=False,
)
answer = agent.run("现在几点？", context=context)
```

 没有配置 API Key 时仍可运行默认的 Mock 演示，方便先理解循环本身。

## 工具运行策略

- `read_only=True` 是默认值，适合查询类工具。
- `read_only=False` 的写工具默认会被 `ToolRegistry` 拦截，只有显式设置 `allow_write_tools=True` 才允许执行。
- `timeout_seconds` 控制单次执行的等待时间，超时会作为 Observation 返回给 LLM。
- `max_attempts` 控制最多执行次数，普通异常会重试，参数错误不会做无意义重试。

## 持久化记忆

`NoteQAAgent.ask()` 会把每轮问题、回答按 `session_id` 写入 SQLite。默认数据库是
`agent_learning/data/conversation_memory.db`，数据库文件已被 `.gitignore` 忽略。

同一个会话跨进程继续追问：

```powershell
python agent_learning/note_qa_agent.py --mock --session-id interview "SQLAlchemy 的 Session 应该怎么管理？"
python agent_learning/note_qa_agent.py --mock --session-id interview "那 flush 和 commit 有什么区别？"
```

交互模式：

```powershell
python agent_learning/note_qa_agent.py --real --interactive --session-id interview
```

使用内存数据库可以关闭持久化：

```powershell
python agent_learning/note_qa_agent.py --mock --memory-db :memory: --session-id temporary "Session 管理"
```

`NoteQAAgent.answer()` 仍然是无状态单轮调用，不会读取或写入历史。

## 滚动摘要记忆

开启 `--summarize-memory` 后，原始消息仍会永久保存在 SQLite；当未压缩历史
达到阈值时，Agent 会把较早的完整问答轮压缩成摘要，并在后续请求中组合使用
“摘要 + 近期原始对话”。默认达到 10 轮触发，最近 5 轮保留原文。

```powershell
python agent_learning/note_qa_agent.py --real --interactive `
  --session-id interview --summarize-memory `
  --summary-trigger-rounds 10 --recent-history-rounds 5
```

摘要写入同一会话的 `conversation_summaries` 表。若摘要模型临时失败，本轮回答
仍会正常返回，摘要指针保持不变，未压缩内容会在后续轮次继续尝试压缩。

## 结构化输出与校验

`structured_output.py` 让 LLM 输出变成可靠接口，四层防御：schema 约束 → JSON 提取 →
Pydantic 严格校验 → 按字段回喂重试。依赖 Pydantic：

```powershell
python -m pip install pydantic
```

```python
from pydantic import Field
from agent_learning.structured_output import StrictModel, structured_call

class NoteCard(StrictModel):
    title: str
    confidence: float = Field(ge=0.0, le=1.0)

response = structured_call(llm, NoteCard, messages, max_attempts=3)
```

工具参数同样要校验（`validate_tool_arguments`），
`to_tool_schema` 可由模型直接生成函数 schema，保证暴露给模型的规则与代码校验同源。

## 检索实操

`retrieval.py` 把“每次遍历目录、在内存里数命中”换成持久化索引：

- **切块**：按 Markdown 标题切分，保留标题面包屑与行号；超长小节按 token 预算继续切，代码块不切断；
- **索引**：SQLite FTS5，必须写 `tokenize='trigram'`——默认的 `unicode61` 不切分中文，`MATCH '缓存'` 实测查不到；
- **检索**：长词走 FTS5 + bm25 排序；短词（不足 3 字符）或 FTS 无结果时回退 `LIKE`；
- **溯源**：每条结果带 `文件:起始行`，行号重叠的结果会被丢弃。

```python
from agent_learning.retrieval import NoteIndex, format_hits

index = NoteIndex('agent_learning/data/notes.db')   # 传 :memory: 用内存索引
index.index_root('obsidian')
hits = index.search('缓存命中', limit=3)
print(format_hits(hits))
```

## 评估与回归

`eval_harness.py` 用“用例 + 基线”回答两个问题：现在好不好、比上次好还是坏。
验收标准是可执行检查（必须包含 / 禁止包含、工具调用、token 上限），不做主观打分。

```python
from agent_learning.eval_harness import EvalCase, Expectation, run_and_compare

cases = [
    EvalCase(
        case_id='session-lifecycle',
        question='Session 应该怎么管理？',
        expectation=Expectation(must_include=('close',), max_tokens=2000),
    ),
]

report, comparison = run_and_compare(
    cases,
    runner,                                          # (case) -> RunResult
    report_path='agent_learning/data/eval_baseline.json',
)
print(comparison)
```

`runner` 由调用方提供（通常把 `NoteQAAgent.ask` 包一层）。单条用例抛异常只记为失败，
不会中断整轮；与基线对比会给出**回归 / 改进 / 新增用例**三张清单。

## 四个主题在 note_qa_agent 汇合

`note_qa_agent.py` 把前面四块拼成一条真实流水线：

```text
问题 → FTS5 检索（带 文件:起始行）→ 按 token 预算分层组装
     → LLM 回答（可选结构化 answer/citations）→ 附来源
```

- **检索**：默认走 `NoteIndex`（FTS5 + trigram 分词器），`--no-index` 可退回旧的
  全量扫描关键词检索；`--rebuild-index` 重建索引，默认库在
  `agent_learning/data/notes.db`（已被 `.gitignore` 忽略）；
- **预算**：`--context-budget` / `--reserve-output` 控制单次请求的 token 预算。
  超预算时先丢对话历史，再丢摘要，最后才动检索片段；系统提示永不裁剪。
  每轮的预算报告在 `agent.last_budget_report`，可以直接进日志；
- **结构化**：`--structured` 让模型返回 `{"answer": ..., "citations": [1, 2]}`，
  校验通过后来源清单只列真正引用的片段；模型不配合就自动退回自由文本，
  所以这个开关不会让 Agent 变得不可用。

```powershell
python agent_learning/note_qa_agent.py --mock "FTS5 中文 分词器"        # 离线看检索
python agent_learning/note_qa_agent.py --real --structured "Session 应该怎么管理？"
python agent_learning/note_qa_agent.py --real --no-index "Session 管理"  # 退回旧检索
```

评估与回归（改 prompt / 换模型之后跑一遍）：

```powershell
python agent_learning/note_qa_eval.py --offline   # 无需 API Key，只验证检索与上下文
python agent_learning/note_qa_eval.py --real      # 端到端回答
```

`--offline` 用一个"把检索到的上下文原样当答案"的假模型，因此它验证的是
**检索与上下文组装有没有退化**，不验证语言质量。报告存成基线，
下次运行会给出回归 / 改进 / 新增用例清单。笔记不在仓库根目录时用
`--note-root` 指定（可重复）。
## 扩展任务

1. 已完成：增加 `get_current_time` 和受限文件读取工具，支持多工具选择
2. 已完成：通过 `--debug-tool-arguments` 观察 `tool_calls.arguments` 的 JSON 字符串到 dict 转换
3. 已完成：工具支持只读 / 可写权限，默认阻止写操作
4. 已完成：工具支持超时与重试，错误会回填给 LLM
5. 已完成：结构化日志记录 Agent、LLM、工具调用、状态和耗时，并自动脱敏
6. 已完成：通过 `RunContext` 给每次请求独立设置工具白名单和写权限
7. 已完成：持久化会话支持滚动摘要压缩，并保留最近原始问答窗口
8. 已完成：token 预算与分层上下文裁剪（`token_budget.py`）
9. 已完成：结构化输出与工具参数校验（`structured_output.py`）
10. 已完成：Markdown 切块 + FTS5 中文检索与段落级溯源（`retrieval.py`）
11. 已完成：用例集、基线报告与回归对比（`eval_harness.py`）
12. 已完成：NoteQAAgent 接入 FTS5 检索、token 预算与结构化回答（`note_qa_agent.py`）
13. 已完成：NoteQAAgent 的用例集与基线回归（`note_qa_eval.py`）
