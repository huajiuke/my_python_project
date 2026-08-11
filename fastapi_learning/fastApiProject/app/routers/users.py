"""用户路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import Pagination, require_login
from app.models import User
from app.schemas import UserOut, UserRegister
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["用户"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=201,
    summary="用户注册",
    description="创建新用户；用户名重复时返回 400。",
)
def register(user: UserRegister, db: Session = Depends(get_db)):
    """注册新用户：查重后写入密码哈希。"""
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    db_user = User(
        username=user.username,
        password=hash_password(user.password),
        age=user.age,
        email=user.email,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get(
    "",
    response_model=list[UserOut],
    summary="用户列表",
    description="分页返回所有用户，不包含密码字段。",
)
def list_users(pagination: Pagination = Depends(), db: Session = Depends(get_db)):
    """分页查询全部用户。"""
    offset = (pagination.page - 1) * pagination.size
    return db.query(User).offset(offset).limit(pagination.size).all()


@router.get(
    "/me",
    response_model=UserOut,
    summary="当前登录用户",
    description="解析 JWT 后返回当前用户；未登录返回 401。",
)
def read_me(current: User = Depends(require_login)):
    """返回当前登录用户。"""
    return current


@router.get(
    "/{user_id}",
    response_model=UserOut,
    summary="按ID查询用户",
    description="按主键查询单个用户；不存在返回 404。",
)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """按主键查询用户。"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user
