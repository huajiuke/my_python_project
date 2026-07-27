"""书签管理器 - ORM 模型定义

SQLAlchemy ORM 的核心思想：
写 Python 类  ->  自动生成 SQL 建表语句
操作 Python 对象  ->  自动转为 INSERT/UPDATE/DELETE/SELECT
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Integer, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    Session,
)


# ── 1. 基类 ──────────────────────────────────
# 所有模型类都要继承这个基类
class Base(DeclarativeBase):
    pass


# ── 2. 用户表 ────────────────────────────────
class User(Base):
    """用户模型 -> 自动生成 users 表"""

    __tablename__ = "users"

    # 字段定义：Python 类型注解 + mapped_column(数据库类型, 约束)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # 关系：这个用户的所有书签
    # relationship 是 ORM 层面的"虚拟字段"，数据库里没有这个列
    bookmarks: Mapped[List["Bookmark"]] = relationship(back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username!r})>"


# ── 3. 书签表 ────────────────────────────────
class Bookmark(Base):
    """书签模型 -> 自动生成 bookmarks 表"""

    __tablename__ = "bookmarks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    # 外键：ForeignKey("users.id") -> 数据库层的约束
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    # 关系：反向指向 User
    user: Mapped["User"] = relationship(back_populates="bookmarks")

    def __repr__(self):
        return f"<Bookmark(id={self.id}, title={self.title!r})>"
