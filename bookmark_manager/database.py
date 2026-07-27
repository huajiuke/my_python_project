"""书签管理器 - 数据库连接与 CRUD 操作"""

from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from bookmark_manager.models import Base, User, Bookmark


engine = create_engine("sqlite:///bookmarks.db", echo=False)
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(bind=engine)


@contextmanager
def get_session():
    """自动提交/回滚/关闭的 Session 上下文"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── 用户 CRUD ────────────────────────────────

def create_user(session: Session, username: str) -> User:
    user = User(username=username)
    session.add(user)
    session.flush()
    print(f"  用户创建成功: {user.username} (id={user.id})")
    return user


def list_users(session: Session) -> List[User]:
    users = session.query(User).all()
    if not users:
        print("  （暂无用户）")
        return []
    for u in users:
        print(f"  [{u.id}] {u.username}  ({len(u.bookmarks)} 个书签)")
    return users


def get_user_by_name(session: Session, username: str) -> Optional[User]:
    return session.query(User).filter(User.username == username).first()


# ── 书签 CRUD ────────────────────────────────

def add_bookmark(session: Session, user_id: int, title: str,
                 url: str, description: str = "") -> Optional[Bookmark]:
    user = session.get(User, user_id)
    if not user:
        print("  用户不存在")
        return None
    bm = Bookmark(title=title, url=url, description=description, user=user)
    session.add(bm)
    print(f"  书签添加成功: {bm.title}")
    return bm


def list_bookmarks(session: Session, user_id: int = None) -> List[Bookmark]:
    query = session.query(Bookmark)
    if user_id:
        query = query.filter(Bookmark.user_id == user_id)

    bookmarks = query.all()
    if not bookmarks:
        print("  （暂无书签）")
        return []

    for bm in bookmarks:
        print(f"  [{bm.id}] {bm.title}  ({bm.url})")
    return bookmarks


def delete_bookmark(session: Session, bookmark_id: int) -> bool:
    bm = session.get(Bookmark, bookmark_id)
    if not bm:
        print(f"  书签 {bookmark_id} 不存在")
        return False
    session.delete(bm)
    print(f"  已删除书签: {bm.title}")
    return True
