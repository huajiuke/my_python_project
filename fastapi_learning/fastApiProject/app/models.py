"""第 6 周 - 第 3 步：FastAPI + SQLAlchemy ORM 模型

你需要在 TODO 处补全代码。
参考：D:/13155/PythonLearn/bookmark_manager/models.py
"""

# 1. 从 datetime 导入 datetime
# 2. 从 typing 导入 List 和 Optional
# 3. 从 sqlalchemy 导入 DateTime, Float, ForeignKey, Integer, String
# 4. 从 sqlalchemy.orm 导入 Mapped, mapped_column, relationship
# 5. 从 database 导入 Base
# TODO: 补全导入
from app.database import Base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String

# 用户表
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # TODO: primary_key=True, autoincrement=True
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)  # TODO: String(50), unique=True, index=True, nullable=False
    password: Mapped[str] = mapped_column(String(100), nullable=False)  # TODO: String(100), nullable=False
    age: Mapped[int] = mapped_column(Integer,default=18)  # TODO: Integer, default=18
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)  # TODO: String(120), nullable=True
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)  # TODO: DateTime, default=datetime.now

    # 一个用户拥有多个商品
    items: Mapped[List["Item"]] = relationship(back_populates="user")  # TODO: back_populates="user"

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username!r})>"


# 商品表
class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)  # TODO: primary_key=True, autoincrement=True
    name: Mapped[str] = mapped_column(String(50),nullable=False)  # TODO: String(50), nullable=False
    price: Mapped[float] = mapped_column(Float, nullable=False)  # TODO: Float, nullable=False
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)  # TODO: ForeignKey("users.id"), nullable=False
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)  # TODO: DateTime, default=datetime.now

    # 商品属于哪个用户
    user: Mapped["User"] = relationship(back_populates="items")  # TODO: back_populates="items"

    def __repr__(self):
        return f"<Item(id={self.id}, name={self.name!r})>"
