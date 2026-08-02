"""第 6 周 - 第 5 步：商品路由（连接数据库）"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies import Pagination
from models import Item, User
from schemas import ItemCreate, ItemOut, ItemUpdate

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
async def list_items(pagination: Pagination = Depends(), db: Session = Depends(get_db)):
    """分页查询商品列表。"""
    offset = (pagination.page - 1) * pagination.size
    items = db.query(Item).offset(offset).limit(pagination.size).all()
    return items


@router.post(
    "/items",
    response_model=ItemOut,
    status_code=status.HTTP_201_CREATED,
    summary="创建商品",
    description="创建商品前校验 user_id 对应的用户是否存在；不存在返回 404。",
)
async def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """创建商品并写入数据库。"""
    if db.get(User, item.user_id) is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    db_item = Item(**item.model_dump())
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
async def read_item(item_id: int, db: Session = Depends(get_db)):
    """按主键查询商品。"""
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    return item


@router.put(
    "/items/{item_id}",
    response_model=ItemOut,
    summary="更新商品",
    description="部分更新商品：只修改请求体里传入的字段。",
)
async def update_item(item_id: int, payload: ItemUpdate, db: Session = Depends(get_db)):
    """更新商品的名称或价格。"""
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除商品",
    description="删除指定商品；不存在返回 404。",
)
async def delete_item(item_id: int, db: Session = Depends(get_db)):
    """删除商品。"""
    item = db.get(Item, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="商品不存在")
    db.delete(item)
    db.commit()
