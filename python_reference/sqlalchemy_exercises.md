# SQLAlchemy 练习题

---

## 练习 1 — 基类的作用

```python
# 写法 A
class User:
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)

# 写法 B
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
```

```
A. 写法 A 也能用，但少了自动建表能力
B. 写法 B 中 Base 的作用是让 SQLAlchemy 识别 User 是个模型，注册到 metadata
C. 两种写法完全等价
D. 写法 B 必须同时写 __tablename__ 和 Mapped，否则报错
```

---

## 练习 2 — mapped_column 的 nullable

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    email: Mapped[Optional[str]]
    age: Mapped[int] = mapped_column(Integer, nullable=True)
```

数据库中哪个字段是非空（NOT NULL）的？

```
A. id 和 name
B. id、name 和 age
C. id、name 和 email
D. 全部都是 NOT NULL
```

---

## 练习 3 — 自动建表时机

```python
Base.metadata.create_all(engine)
```

这行代码的作用是：

```
A. 每次运行都 DROP 所有表再重建
B. 只创建数据库中不存在的表，已存在的不动
C. 如果模型加了新字段，自动 ALTER TABLE 加列
D. 只在第一次运行时有效，之后什么都不做
```

---

## 练习 4 — 一对多关系

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    articles: Mapped[List["Article"]] = relationship(back_populates="author")

class Article(Base):
    __tablename__ = "articles"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["User"] = relationship(back_populates="articles")
```

选出正确的：

```
A. ForeignKey 是 ORM 层面的虚拟字段，数据库没有实际约束
B. relationship 是数据库层面的外键约束
C. ForeignKey 是数据库约束，relationship 是 ORM 层面的对象导航
D. user_id 不需要 ForeignKey 也能用 relationship
```

---

## 练习 5 — 查询用户

```python
session.query(User).filter(User.age > 18).all()
```

这段代码生成的 SQL 大致是：

```
A. SELECT * FROM users
B. SELECT * FROM users WHERE age > 18
C. SELECT id, name FROM users WHERE age > 18
D. SELECT * FROM users HAVING age > 18
```

---

## 练习 6 — flush 与 commit

```python
def create_user(session, username):
    user = User(username=username)
    session.add(user)
    session.flush()
    print(user.id)
    return user
```

`session.flush()` 的作用是：

```
A. 将 INSERT 发送到数据库，user.id 获得值，但事务未提交
B. 将 INSERT 发送到数据库并提交事务
C. 将 user 从 session 中移除
D. 刷新 user 对象的属性为数据库中的值
```

---

## 练习 7 — 自动回滚

```python
@contextmanager
def get_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()

with get_session() as db:
    user = User(username="alice")
    db.add(user)
    raise RuntimeError("出错了")
```

数据库最终会：

```
A. 成功插入 alice
B. 不会插入 alice（事务被回滚）
C. 报错但不影响数据库
D. 部分插入 alice 的数据
```

---

## 练习 8 — 查询单条

获取第一条满足条件的记录，正确的写法是：

```
A. session.query(User).filter(User.id == 1).one()
B. session.query(User).filter(User.id == 1).first()
C. session.query(User).filter(User.id == 1).get()
D. B 和 C 都可以，但语义不同
```

---

## 练习 9 — 删除记录

```python
# 操作 A
user = session.query(User).filter(User.id == 1).first()
session.delete(user)
session.commit()

# 操作 B
session.query(User).filter(User.id == 1).delete()
session.commit()
```

选出正确的：

```
A. 操作 A 需要先查出对象再删，操作 B 直接发 DELETE SQL，更高效
B. 两种操作完全等价
C. 操作 B 需要先 flush 才能用
D. 操作 A 只适用于设置了 relationship 的模型
```

---

## 练习 10 — relationship 的懒加载

```python
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    articles: Mapped[List["Article"]] = relationship(back_populates="author")

with get_session() as db:
    user = db.query(User).first()
    print(user.articles)  # 这行会怎么样？
```

假设 session 已正常关闭，选出正确的：

```
A. user.articles 直接拿到列表，不会执行额外 SQL
B. user.articles 会触发新的 SQL 查询去 articles 表取数据
C. user.articles 报错，因为 session 已关闭不能惰性加载
D. user.articles 返回 None
```

---

## 练习 11 — 排序

按创建时间倒序排列用户的正确写法：

```
A. session.query(User).order_by(User.created_at).all()
B. session.query(User).order_by(User.created_at.desc()).all()
C. session.query(User).sort_by(User.created_at.desc()).all()
D. session.query(User).desc(User.created_at).all()
```

---

## 练习 12 — 更新字段

将 id=1 的用户名改为 "bob"，正确的做法是：

```
A. user = session.get(User, 1); user.name = "bob"; session.flush()
B. user = session.get(User, 1); user.name = "bob"; session.commit()
C. session.query(User).filter(User.id == 1).update(name="bob"); session.commit()
D. session.update(User).set(name="bob").where(User.id == 1)
```

---

## 练习 13 — 级联删除

```python
class User(Base):
    __tablename__ = "users"
    articles: Mapped[List["Article"]] = relationship(
        back_populates="author", cascade="all, delete"
    )
```

`cascade="all, delete"` 的作用是：

```
A. 删除 User 时自动删除其所有 Article
B. 删除 Article 时自动删除其 User
C. 查询 User 时自动加载 Article
D. 更新 User 时自动更新 Article
```

---

## 练习 14 — 开启 echo 查看 SQL

```python
engine = create_engine("sqlite:///data.db", echo=True)
```

`echo=True` 的作用是：

```
A. 数据库会返回更详细的错误信息
B. SQLAlchemy 执行的每条 SQL 语句会打印到控制台
C. 数据库连接会打印日志
D. session.add() 会有声音提示
```

---

## 练习 15 — scoped_session

```python
SessionFactory = sessionmaker(bind=engine)
SessionGlobal = scoped_session(SessionFactory)
```

`scoped_session` 解决的核心问题是：

```
A. 让 session 启动速度更快
B. 多线程环境下每个线程获取自己的 session，互不干扰
C. 让 session 支持异步操作
D. 自动将 session 绑定到数据库表
```

---

## 答案

1-B  2-A  3-B  4-C  5-B  6-A  7-B  8-D  9-A  10-C  11-B  12-B  13-A  14-B  15-B
