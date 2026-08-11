import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


class Pagination:
    def __init__(self, page: int = 1, size: int = 10):
        self.page = max(page, 1)
        self.size = min(max(size, 1), 100)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    # TODO:
    # 1. try: user_id = decode_access_token(token)
    # 2. except (jwt.PyJWTError, KeyError, TypeError, ValueError):
    #        raise HTTPException(401, "无效的认证凭证")
    # 3. user = db.get(User, user_id)，不存在则 401
    # 4. return user
    try:
        user_id = decode_access_token(token)
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        raise HTTPException(401, "无效的认证凭证")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(401, "用户不存在")
    return user


def require_login(user: User = Depends(get_current_user)):
    return user
