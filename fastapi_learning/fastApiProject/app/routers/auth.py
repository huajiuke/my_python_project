"""认证路由。"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import Token
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post(
    "/login",
    response_model=Token,
    summary="登录并获取JWT",
    description="使用表单提交 username 和 password；密码正确返回 access_token。",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """校验密码并签发 JWT。"""
    user = db.query(User).filter(User.username == form_data.username).first()
    if user is None or not verify_password(form_data.password, user.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(user.id)
    return Token(access_token=token)
