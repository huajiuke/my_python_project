"""第 6 周 - 第 5 步：用户路由（连接数据库）

你需要在 TODO 处补全代码。
"""

# 1. from fastapi import APIRouter, Depends, HTTPException
# 2. from sqlalchemy.orm import Session
# 3. from database import get_db
# 4. from dependencies import require_login
# 5. from models import User
# 6. from schemas import UserOut, UserRegister
# TODO: 补全导入
from fastapi import APIRouter, Depends, HTTPException
from database import get_db
from sqlalchemy.orm import Session
from schemas import UserOut, UserRegister
from models import User
from dependencies import require_login
router = APIRouter(prefix="/users", tags=["用户"])


@router.post(
    "/register",
    response_model=UserOut,
    status_code=201,
    summary="用户注册",
    description="创建新用户；用户名重复时返回 400。",
)
async def register(user: UserRegister, db: Session = Depends(get_db)):
    """注册新用户：查重后写入数据库。"""
    # TODO:
    # 1. 用 db.query(User).filter(User.username == user.username).first() 查重
    # 2. 已存在 -> raise HTTPException(400, "用户名已存在")
    # 3. db_user = User(**user.model_dump())
    # 4. db.add(db_user); db.commit(); db.refresh(db_user)
    # 5. return db_user
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(400, "用户名已存在")
    db_user = User(**user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.get(
    "",
    response_model=list[UserOut],
    summary="用户列表",
    description="返回所有用户，不包含密码字段。",
)
async def list_users(db: Session = Depends(get_db)):
    """查询全部用户。"""
    # TODO: return db.query(User).all()
    return db.query(User).all()


@router.get(
    "/me",
    response_model=UserOut,
    summary="当前登录用户",
    description="根据 Authorization 请求头解析出的用户名查询当前用户；未登录返回 401。",
)
async def read_me(current: dict = Depends(require_login), db: Session = Depends(get_db)):
    """返回当前登录用户的资料。"""
    # TODO: 按 current["username"] 查询当前用户，不存在则 404
    user = db.query(User).filter(User.username == current["username"]).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    return user


@router.get(
    "/{user_id}",
    response_model=UserOut,
    summary="按ID查询用户",
    description="按主键查询单个用户；不存在返回 404。",
)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """按主键查询用户。"""
    # TODO: db.get(User, user_id)，不存在则 404
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "用户不存在")
    return user
