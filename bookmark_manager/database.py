"""书签管理器 - 数据库连接与 CRUD 操作"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from bookmark_manager.models import Base, User, Bookmark


# ── 数据库初始化 ──────────────────────────────

def init_db(db_path: str = "bookmarks.db") -> Session:
    """创建数据库连接、建表、返回 Session"""
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)      # 自动建表（CREATE TABLE IF NOT EXISTS）
    session = Session(engine)
    return session


# ── 用户 CRUD ────────────────────────────────

def create_user(session: Session, username: str) -> User:
    """创建用户"""
    user = User(username=username)
    session.add(user)
    session.commit()
    print(f"  用户创建成功: {user.username} (id={user.id})")
    return user


def list_users(session: Session) -> List[User]:
    """列出所有用户"""
    users = session.query(User).all()
    if not users:
        print("  （暂无用户）")
        return []
    for u in users:
        print(f"  [{u.id}] {u.username}  ({len(u.bookmarks)} 个书签)")
    return users


def get_user_by_name(session: Session, username: str) -> Optional[User]:
    """按用户名查找"""
    return session.query(User).filter(User.username == username).first()


# ── 书签 CRUD ────────────────────────────────

def add_bookmark(session: Session, user: User, title: str,
                 url: str, description: str = "") -> Bookmark:
    """给指定用户添加书签"""
    bm = Bookmark(title=title, url=url, description=description, user=user)
    session.add(bm)
    session.commit()
    print(f"  书签添加成功: {bm.title}")
    return bm


def list_bookmarks(session: Session, user: User = None) -> List[Bookmark]:
    """列书签，可选按用户过滤"""
    query = session.query(Bookmark)
    if user:
        query = query.filter(Bookmark.user_id == user.id)

    bookmarks = query.all()
    if not bookmarks:
        print("  （暂无书签）")
        return []

    for bm in bookmarks:
        print(f"  [{bm.id}] {bm.title}  ({bm.url})  - {bm.user.username}")
    return bookmarks


def delete_bookmark(session: Session, bookmark_id: int) -> bool:
    """按 ID 删除书签"""
    bm = session.query(Bookmark).filter(Bookmark.id == bookmark_id).first()
    if not bm:
        print(f"  书签 {bookmark_id} 不存在")
        return False
    session.delete(bm)
    session.commit()
    print(f"  已删除书签: {bm.title}")
    return True
