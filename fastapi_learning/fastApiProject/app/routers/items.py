"""商品路由。"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import Pagination, require_login
from app.models import Item, User
from app.schemas import ItemCreate, ItemOut, ItemUpdate

router = APIRouter(tags=["商品"])


@router.get(
    "/news",
    summary="新闻列表（查询参数示例）",
    description="演示 Query 查询参数：skip 跳过的记录数，limit 返回的记录数。",
)
async def get_news(
    skip: int = Query(0, description="跳过的记录数", ge=0, lt=100),
    limit: int = Query(10, description="返回的记录数", ge=1, le=100),
):
    """返回查询参数示例。"""
    return {"skip": skip, "limit": limit}


@router.get(
    "/items",
    response_model=list[ItemOut],
    summary="商品分页列表",
    description="使用分页依赖 Pagination，按 page 和 size 返回商品。",
)
def list_items(pagination: Pagination = Depends(), db: Session = Depends(get_db)):
    """分页查询商品列表。"""
    offset = (pagination.page - 1) * pagination.size
    return db.query(Item).offset(offset).limit(pagination.size).all()


@router.post(
    "/items",
    response_model=ItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建商品",
    description="需要登录；商品归属当前登录用户。",
)
def create_item(
    item: ItemCreate,
    current: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """创建当前用户的商品。"""
    db_item = Item(**item.model_dump(), user_id=current.id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get(
    "/items/{item_id}",
    response_model=ItemOut,
    summary="查询单个商品",
    description="按主键查询商品；不存在返回 404。",
)
def read_item(item_id: int, db: Session = Depends(get_db)):
    """按主键查询商品。"""
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return item


@router.put(
    "/items/{item_id}",
    response_model=ItemOut,
    summary="更新商品",
    description="只能更新自己创建的商品。",
)
def update_item(
    item_id: int,
    payload: ItemUpdate,
    current: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """部分更新自己的商品。"""
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    if item.user_id != current.id:
        raise HTTPException(status_code=403, detail="无权操作该商品")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除商品",
    description="只能删除自己创建的商品。",
)
def delete_item(
    item_id: int,
    current: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    """删除自己的商品。"""
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    if item.user_id != current.id:
        raise HTTPException(status_code=403, detail="无权操作该商品")
    db.delete(item)
    db.commit()
