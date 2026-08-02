from fastapi import Depends, Header, HTTPException


class Pagination:
    def __init__(self, page: int = 1, size: int = 10):
        self.page = max(page, 1)
        self.size = min(max(size, 1), 100)


def get_current_user(authorization: str | None = Header(None)):
    if authorization is None:
        raise HTTPException(status_code=401, detail="缺少认证信息")
    # 演示用：实际项目应从 token 中解析用户
    return {"username": "zhangsan", "token": authorization}


def require_login(user: dict = Depends(get_current_user)):
    return user
