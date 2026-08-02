"""第 6 周 - 第 4 步：FastAPI Pydantic 请求/响应模型

你需要在 TODO 处补全代码。
UserRegister 已作为示例保留，其余模型按这个模式补全。
"""

# 1. 从 datetime 导入 datetime
# 2. 从 pydantic 导入 BaseModel 和 Field
# TODO: 补全导入
from datetime import datetime
from pydantic import BaseModel, Field

# 注册请求体（示例，已完整）
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, description="用户名")
    password: str = Field(..., min_length=6, max_length=100, description="密码")
    age: int = Field(18, ge=0, le=150, description="年龄")
    email: str | None = Field(None, pattern=r"^\S+@\S+\.\S+$", description="邮箱")


# 用户响应体：注意不能返回 password
class UserOut(BaseModel):
    id: int
    username: str
    age: int
    email: str | None = None
    created_at: datetime


# 创建商品请求体：需要包含所属用户 user_id
class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50, description="商品名称")  # TODO: min_length=1, max_length=50, description="商品名称"
    price: float = Field(..., ge=0, description="商品价格")  # TODO: ge=0, description="商品价格"
    user_id: int = Field(..., description="所属用户ID")  # TODO: description="所属用户ID"


# 更新商品请求体：字段可选，只更新传进来的字段
class ItemUpdate(BaseModel):
    name: str | None = Field(None)  # TODO: min_length=1, max_length=50
    price: float | None = Field(None)  # TODO: ge=0


# 商品响应体
class ItemOut(BaseModel):
    id: int
    name: str
    price: float
    user_id: int
    created_at: datetime
