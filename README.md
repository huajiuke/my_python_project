# Python 后端求职学习计划（定制版）

> 背景：运维岗（云软件变更）→ 后端开发
> 时间：周内 1-2h/天 + 周末 8h/天 ≈ 20-24h/周
> 优势：已有 Linux/网络/部署经验，后端学习的「下半身」你已经有了

---

## 一、路线选择

| 岗位 | 优先级 | 原因 |
|------|--------|------|
| **Python后端开发** | 主攻 | 你的运维经验（部署、网络、服务器）是天然优势 |
| 自动化/工具开发 | 辅助了解 | 作为补充技能组合 |
| 数据分析 | 了解即可 | 知道 Pandas 基本操作，不深入 |

---

## 二、项目与知识点完成情况

### ✅ 阶段一：基础巩固（完成）

| 项目 | 知识点 | 状态 |
|------|--------|------|
| **task_manager** | 类、对象、实例方法、`__str__`/`__repr__`、`@classmethod`、枚举 Enum | ✅ |
| | JSON 序列化/反序列化、uuid、datetime、pathlib | ✅ |
| | f-string / .format()、类型提示 | ✅ |
| | 包与模块组织、`__init__.py`、`python -m` 运行 | ✅ |
| | 虚拟环境 venv、requirements.txt | ✅ |
| | 异常处理 try/except、自定义异常 | ✅ |
| | Git 分支、合并、PR 流程 | ✅ |
| **知识库** | `docs/knowledge_notes.md` — 继承、装饰器、上下文管理器、生成器、迭代器 | 📝 |
| | `docs/knowledge_first_week.md` — 已学知识点 + 代码样例 | 📝 |
| | `python_reference/magic_methods.md` — 魔术方法速查表 | 📝 |

### ✅ 阶段二：数据库与 SQLAlchemy ORM（完成）

| 项目 | 知识点 | 状态 |
|------|--------|------|
| **bookmark_manager** | SQLAlchemy ORM：Engine、Session、DeclarativeBase | ✅ |
| | Mapped + mapped_column 字段定义 | ✅ |
| | ForeignKey + relationship 一对多关系 | ✅ |
| | CRUD：增删改查完整操作 | ✅ |
| | `sessionmaker` + `scoped_session` 工厂模式 | ✅ |
| | `@contextmanager` 自动提交/回滚/关闭 Session | ✅ |
| | `session.flush()` vs `session.commit()` 的区别 | ✅ |
| **知识库** | `python_reference/sqlalchemy_guide.md` — ORM 速查 + 综合示例 | 📝 |

### 🚧 阶段三：后端开发 FastAPI（进行中）

| 周次 | 内容 |
|------|------|
| 第5周 | HTTP、RESTful API、FastAPI 路由与参数 |
| 第6周 | Pydantic 模型 + FastAPI + SQLAlchemy 集成 |
| 第7周 | JWT 用户认证、密码哈希 |
| 第8周 | 依赖注入、错误处理、中间件 |
| 第9-10周 | Docker 部署 FastAPI + MySQL |
| 学习目录 | `fastapi_learning/`：基础/进阶/SQLAlchemy/JWT 笔记 + `fastApiProject/` 示例代码 | 🚧 |

### 🔲 阶段四：扩展进阶

| 周次 | 内容 |
|------|------|
| 第11周 | Redis 缓存 |
| 第12周 | 异步编程、Celery |

### 📖 AI Agent 补充知识（面试了解）

| 内容 | 状态 |
|------|------|
| AI Agent 核心概念、架构模式、框架对比、面试题 | ✅ [knowledge_ai_agent.md](docs/knowledge_ai_agent.md) |

### 🔄 贯穿全程

| 内容 | 状态 |
|------|------|
| LeetCode 刷题 | ✅ 本地测试工具已就绪 `leetcode_tool/` |
| Python 八股文 | 📝 知识库持续积累中 |

---

## 三、Workspace 目录结构

```
D:\13155\PythonLearn/
├── README.md                        # 学习计划
├── requirements.txt                 # 依赖清单
├── .gitignore
├── venv/                            # 虚拟环境
│
├── task_manager/                    # 阶段一：CLI 任务管理器
│   ├── __init__.py / __main__.py
│   ├── models.py / storage.py
│
├── bookmark_manager/                # 阶段二：书签管理器 (SQLAlchemy)
│   ├── __init__.py / __main__.py
│   ├── models.py / database.py
│
├── leetcode_tool/                   # 本地 LeetCode 测试工具
│   ├── structures.py                #   ListNode / TreeNode 互转
│   ├── runner.py                    #   测试运行器
│   └── problems/                    #   题目文件
│       ├── example.py               #   3 道示例题
│       └── mergeKLists.py           #   合并 K 个升序链表
│
├── python_reference/                # Python 知识库
│   ├── magic_methods.md
│   └── sqlalchemy_guide.md
│
├── docs/                            # 学习文档与简历
│   ├── knowledge_notes.md
│   ├── knowledge_first_week.md
│   ├── knowledge_ai_agent.md
│   └── resume_python_backend_dev.md
│
├── fastapi_learning/                # 阶段三：FastAPI
│   ├── 1.Fasapi基础.md               # FastAPI 基础笔记
│   ├── 2.FastApi进阶.md              # FastAPI 进阶笔记
│   ├── 3.FastApi+SQLAlchemy.md       # FastAPI + SQLAlchemy 集成笔记
│   ├── 4.Pydantic练习.md             # Pydantic 练习题
│   ├── 5.JWT认证.md                  # JWT 认证完整流程
│   └── fastApiProject/               # FastAPI 示例项目
│       ├── main.py                   # 应用入口
│       ├── test_main.http            # HTTP 测试文件
│       ├── tests/                    # pytest 自动化测试
│       └── app/                      # 业务代码
│           ├── database.py
│           ├── models.py
│           ├── schemas.py
│           ├── security.py
│           ├── dependencies.py
│           ├── middleware.py
│           ├── routers/
│           ├── static/
│           ├── requirements.txt
│           ├── requirements-dev.txt
│           └── API文档.md
```

---

## 四、学习节奏模板

### 周内（每天1-2h）
```
19:00-19:10  回顾昨天
19:10-20:00  学新内容（看文档/视频 + 写代码）
20:00-20:30  做练习题或 LeetCode
20:30-20:40  整理笔记 / 提交代码
```

### 周末（每天8h）
```
上午 09:00-12:00  项目开发（核心产出时间）
下午 14:00-17:00  项目开发 / 复习本周知识
晚上 19:30-21:30  刷题 + 下周预习
```

---

## 五、配套知识库

| 文件 | 内容 |
|------|------|
| `docs/knowledge_notes.md` | 第1-2周待学知识点：继承、装饰器、上下文管理器、生成器、迭代器、异常处理、venv、Git分支 |
| `docs/knowledge_first_week.md` | 第1周已学知识点含代码样例+综合练习 |
| `python_reference/magic_methods.md` | 7 类常用魔术方法速查表 |
| `python_reference/sqlalchemy_guide.md` | SQLAlchemy ORM 框架指南 + 综合示例 |
| `docs/knowledge_ai_agent.md` | AI Agent 学习笔记：概念、架构模式、框架对比、面试题 + 代码示例 |

---

## 六、GitHub

所有代码已上传：[https://github.com/huajiuke/my_python_project](https://github.com/huajiuke/my_python_project)
