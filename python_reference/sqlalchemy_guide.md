# SQLAlchemy ORM 速查

> 版本：2.0+（本项目使用的最新风格）
> 对应项目：bookmark_manager

---

## 一、整体架构

```
应用代码 (Python 对象)
      ↕   ORM 层：对象 ↔ SQL 的自动映射
SQLAlchemy Core (SQL 表达式引擎)
      ↕   数据库驱动
SQLite / MySQL / PostgreSQL
```

**ORM 做的事**：你操作 Python 对象，它自动翻译成 SQL 语句发给数据库。

---

## 二、核心概念

### Engine（引擎）

数据库连接的源头。一个 Engine 对应一个数据库。

```python
from sqlalchemy import create_engine

# SQLite（文件型）
engine = create_engine("sqlite:///data.db")

# MySQL
engine = create_engine("mysql+pymysql://user:pass@localhost/db")

# PostgreSQL
engine = create_engine("postgresql://user:pass@localhost/db")
```

### Session（会话）

所有数据库操作的入口。增删改查都通过 Session。

```python
from sqlalchemy.orm import Session

session = Session(engine)
session.add(user)
session.commit()
```

### DeclarativeBase + Model（模型）

一个 Python 类 = 一张数据库表。类的属性 = 表的字段。

```python
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"          # 表名
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
```

### Mapped + mapped_column（SQLAlchemy 2.0 风格）

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    age: Mapped[Optional[int]]         # 可为空的字段，不写 mapped_column 会自动推断类型
```

类型注解 `Mapped[类型]` 告诉 ORM 这个字段的类型，`mapped_column()` 定义数据库层面的细节（长度、约束等）。

---

## 三、字段类型与约束

```python
from sqlalchemy import String, Integer, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import mapped_column
from datetime import datetime

class Example(Base):
    __tablename__ = "examples"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    age: Mapped[Optional[int]]                           # 可为空
    score: Mapped[float] = mapped_column(Float, default=0.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    bio: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # 外键
```

### 常用约束速查

| 参数 | 作用 |
|------|------|
| `primary_key=True` | 主键 |
| `autoincrement=True` | 自增 |
| `nullable=False` | 非空 |
| `unique=True` | 唯一约束 |
| `default=值` | 默认值 |
| `index=True` | 加索引 |

---

## 四、CRUD 操作

### Create

```python
user = User(username="alice")
session.add(user)       # 加入会话
session.commit()        # 提交事务，写入数据库
# 此时 user.id 自动有了值
```

批量添加：

```python
users = [User(username="a"), User(username="b")]
session.add_all(users)
session.commit()
```

### Read

```python
# 查全部
all_users = session.query(User).all()

# 按条件过滤
user = session.query(User).filter(User.username == "alice").first()

# 多条件
users = session.query(User).filter(User.age >= 18, User.is_active == True).all()

# 排序
users = session.query(User).order_by(User.created_at.desc()).all()

# 限制条数
users = session.query(User).limit(5).all()
```

SQLAlchemy 2.0 的 `select()` 风格（等价）：

```python
from sqlalchemy import select

stmt = select(User).where(User.username == "alice")
user = session.execute(stmt).scalar_one()
```

### Update

```python
# 方式一：查到对象，改属性，提交
user = session.query(User).filter(User.id == 1).first()
user.username = "new_name"
session.commit()

# 方式二：直接更新（一条 SQL）
session.query(User).filter(User.id == 1).update({"username": "new_name"})
session.commit()
```

### Delete

```python
# 先查再删
user = session.query(User).filter(User.id == 1).first()
session.delete(user)
session.commit()

# 直接删
session.query(User).filter(User.id == 1).delete()
session.commit()
```

---

## 五、关系（Relationships）

### 一对多（User -> Bookmark）

**models.py 定义：**

```python
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str]

    # "虚拟字段"，数据库里没有这个列
    # 但可以通过 user.bookmarks 拿到该用户的所有书签
    bookmarks: Mapped[List["Bookmark"]] = relationship(back_populates="user")


class Bookmark(Base):
    __tablename__ = "bookmarks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))  # 真实的数据库外键

    user: Mapped["User"] = relationship(back_populates="bookmarks")
```

**使用：**

```python
# 正向：通过书签找到所属用户
bm = session.get(Bookmark, 1)
print(bm.user.username)       # 自动查 users 表，拿到 User 对象

# 反向：通过用户找到所有书签
user = session.get(User, 1)
print(user.bookmarks)          # 自动查 bookmarks 表，拿到 Bookmark 列表
```

### 外键 vs relationship 的区别

| | ForeignKey | relationship |
|---|---|---|
| 层面 | 数据库约束 | ORM 层面的便利工具 |
| 表里有什么 | 一个 user_id 列 | 什么都没有 |
| 作用 | 保证数据完整性 | 让你能写 `user.bookmarks` 直接拿到关联数据 |
| 必须吗 | 必须 | 可选，不写也能用，但得自己查 |

---

## 六、会话生命周期

```python
# 正确做法：每次操作创建新的 Session
def add_user(username):
    engine = create_engine("sqlite:///data.db")
    with Session(engine) as session:
        user = User(username=username)
        session.add(user)
        session.commit()
        return user

# 或者全局一个 Session，但要注意提交/回滚
session = Session(engine)
try:
    user = User(username="alice")
    session.add(user)
    session.commit()
except:
    session.rollback()   # 出错时回滚
    raise
```

**关键规则**：`add()` 后必须 `commit()`，否则数据不会真正写入数据库。`commit()` 后 Session 里的对象仍然可以访问。

---

## 七、自动建表

```python
# 一行代码，创建所有未存在的表
Base.metadata.create_all(engine)

# 相当于执行了所有模型的 CREATE TABLE IF NOT EXISTS
```

创建表之后如果修改了模型（比如加了字段），`create_all` 不会自动 ALTER TABLE。需要手动删表重建或使用迁移工具（Alembic）。

---

## 八、完整示例：用 SQLAlchemy 2.0 风格写一个迷你项目

```python
"""SQLAlchemy 综合示例：借阅管理系统"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import create_engine, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import (
    DeclarativeBase, Session,
    Mapped, mapped_column, relationship,
)

# ── 1. 基类 ──
class Base(DeclarativeBase):
    pass

# ── 2. 模型 ──
class Reader(Base):
    __tablename__ = "readers"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    books: Mapped[List["Book"]] = relationship(back_populates="borrower")

class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    author: Mapped[str] = mapped_column(String(100))
    borrower_id: Mapped[Optional[int]] = mapped_column(ForeignKey("readers.id"), nullable=True)
    borrower: Mapped[Optional["Reader"]] = relationship(back_populates="books")
    borrowed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

# ── 3. 使用 ──
engine = create_engine("sqlite:///library.db", echo=True)
Base.metadata.create_all(engine)

session = Session(engine)

# 创建读者
alice = Reader(name="Alice")
bob = Reader(name="Bob")
session.add_all([alice, bob])
session.commit()

# 创建书籍并借出
book1 = Book(title="Python入门", author="张三", borrower=alice, borrowed_at=datetime.now())
book2 = Book(title="SQL必知必会", author="李四", borrower=bob, borrowed_at=datetime.now())
book3 = Book(title="设计模式", author="王五")
session.add_all([book1, book2, book3])
session.commit()

# 查询：Alice 借了哪些书
alice = session.query(Reader).filter(Reader.name == "Alice").first()
for book in alice.books:
    print(f"  {book.title} - {book.author}")

# 查询：未被借出的书
available = session.query(Book).filter(Book.borrower_id == None).all()
for book in available:
    print(f"  可借: {book.title}")

# 还书
book1.borrower = None
book1.borrowed_at = None
session.commit()

session.close()
```
