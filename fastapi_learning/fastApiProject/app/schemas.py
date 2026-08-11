"""FastAPI Pydantic 请求/响应模型。"""

from datetime import datetime

from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    password: str = Field(..., min_length=6, max_length=72, description="密码")
    age: int = Field(18, ge=0, le=150, description="年龄")
    email: str | None = Field(None, pattern=r"^\S+@\S+\.\S+$", description="邮箱")


class UserOut(BaseModel):
    id: int
    username: str
    age: int
    email: str | None = None
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="商品名称")
    price: float = Field(..., ge=0, description="商品价格")


class ItemUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50, description="商品名称")
    price: float | None = Field(None, ge=0, description="商品价格")


class ItemOut(BaseModel):
    id: int
    name: str
    price: float
    user_id: int
    created_at: datetime
