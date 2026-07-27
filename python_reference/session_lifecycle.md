# SQLAlchemy Session 生命周期详解

---

## 一、Session 是什么

Session 不是"数据库连接"。它做三件事：

1. **缓存** — `session.add(user)` 后，user 存在 Session 内部的 Map 里，还没发给数据库
2. **变更跟踪** — 改了 `user.name = "bob"`，Session 知道对象变了，commit 时自动发 UPDATE
3. **事务管理** — 所有操作在同一个事务里，要么全成功要么全失败

---

## 二、对象的 4 种状态

```
新建对象
    │
    ▼
┌─────────────┐    session.add()    ┌───────────┐
│  Transient  │ ──────────────────→ │  Pending  │
│  （瞬态）    │                     │  （挂起）   │
└─────────────┘                     └─────┬─────┘
       ↑                                  │
       │                            session.flush()
       │                                  │
       │                                  ▼
       │                            ┌───────────┐
       │      session.close()       │ Persistent│
       │      cache clear           │  （持久）   │
       │                            └─────┬─────┘
       │                                  │
       │                                  │ commit
       │                                  ▼
       └──────────────────────────────┌───────────┐
                                     │  Detached │
                                     │  （游离）   │
                                     └───────────┘
```

### 瞬态（Transient）

```python
user = User(username="alice")
# 没有被任何 Session 管理
# user.id = None
# 改属性不会同步到数据库
```

### 挂起（Pending）

```python
session.add(user)
# 进入 Session 缓存，但 SQL 还没发到数据库
# user.id 仍然是 None
# 可以继续改属性或 add 其他对象
```

### 持久（Persistent）

```python
session.flush()
# 或 session.commit()（内部会先 flush）
# INSERT 已发给数据库
# user.id 有值了
# Session 持续跟踪 user 的所有属性变更
```

### 游离（Detached）

```python
session.close()
# Session 不再管理这个对象
# user.id 有值，但改属性不会自动同步
# 访问懒加载属性（如 user.articles）会报错
# 普通属性（user.username）还能访问（在内存里）
```

---

## 三、flush 和 commit 的区别

| | flush | commit |
|---|---|---|
| 做了什么 | 将缓存的 SQL 发给数据库执行 | flush + 提交事务 |
| 数据可见性 | 当前事务内可见，其他连接看不到 | 所有连接都能看到 |
| 能否回滚 | 可以 rollback 撤销 | 事务结束，无法回滚 |
| 自增 id 赋值 | ✅ 会赋值 | ✅ 也会（commit 内部先 flush） |
| 何时用 | 需要在事务中间拿 id，但还没做完其他操作 | 确认所有操作完成，要落地了 |

### 关键：commit 内部自动调 flush

```python
session.add(user)
session.commit()   # 等价于 session.flush() + 事务提交
```

所以绝大多数时候你只需要 `commit()`。

### 唯一需要 flush 的场景

要在事务中间拿 id，但还不结束事务：

```python
def create_user(session, username):
    user = User(username=username)
    session.add(user)
    session.flush()          # 发 INSERT，拿到 id
    print(f"id={user.id}")   # 能打印了
    return user
    # commit 由外层 get_session() 统一做
```

---

## 四、contextmanager 封装 Session

### 不封装的写法（每次都要重复 8 行）

```python
session = SessionLocal()
try:
    user = User(username="alice")
    session.add(user)
    session.commit()
except Exception:
    session.rollback()
    raise
finally:
    session.close()
```

### 封装后

```python
@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()       # 正常 → 提交
    except Exception:
        session.rollback()     # 异常 → 回滚
        raise
    finally:
        session.close()        # 无论成败 → 关闭

# 使用
with get_session() as db:
    db.add(user)
    # 出异常自动回滚，正常自动提交，都会自动 close
```

### 为什么要封装

- **防止泄漏**：有人忘了 close，连接池会被撑爆
- **统一错误处理**：所有异常的 rollback 由一处处理
- **减少重复**：不用每次写 8 行模板代码

---

## 五、Session 关闭后为什么不能访问 relationship

```python
with get_session() as db:
    user = db.query(User).first()
    # 此时 user 是持久状态

# with 块结束 → commit → close
# user 变成游离状态

print(user.username)    # ✅ 普通属性在内存里，可以访问
print(user.articles)    # ❌ 懒加载，需要查数据库，但 session 已关
```

默认的 `relationship` 是**懒加载**（lazy loading）：访问时才查数据库。session 关闭后查不了，报 `DetachedInstanceError`。

### 解决：在 session 关闭前主动加载

```python
with get_session() as db:
    user = db.query(User).first()
    articles = list(user.articles)   # 先取出来变成普通列表

# session 关闭后
print(articles)  # ✅ 正常的 Python 列表，不受影响
```

---

## 六、完整流程示例

```python
# === 瞬态 ===
user = User(username="alice")
print(user.id)          # None
print(session in user)  # False

# === add → 挂起 ===
session.add(user)
print(user.id)          # None（还没 INSERT）
print(session.is_modified(user))  # True

# === flush → 持久 ===
session.flush()
print(user.id)          # 1（自增 ID 回来了）

# 继续修改 — Session 自动跟踪
user.username = "alice_modified"
# Session 记下了变更

# === commit ===
session.commit()
# UPDATE 发出，事务提交
# 其他连接能看到数据了

# === close → 游离 ===
session.close()

# 普通属性还能读
print(user.username)    # "alice_modified"

# 但不能用来操作数据库
session.add(user)       # ❌ 报错，DetachedInstanceError
```

---

## 七、速查表

| 概念 | 一句话 |
|------|--------|
| Session | 缓存 + 变更跟踪 + 事务管理器 |
| add | 把对象放缓存，标记为"待插入" |
| flush | 发 SQL 到数据库（拿 id），不提交事务 |
| commit | flush + 提交事务，数据对其他连接可见 |
| close | 清缓存，对象变游离态 |
| 瞬态 | 新建对象，未被 Session 管理，id=None |
| 挂起 | 已 add，但还没 flush，id=None |
| 持久 | 已 flush，id 有值，Session 跟踪变更 |
| 游离 | Session 关闭，普通属性可读但不能操作数据库 |
| 懒加载 | 访问 relationship 时才查数据库，Session 关闭后报错 |
| contextmanager | 封装 commit/rollback/close，防止泄漏 |
