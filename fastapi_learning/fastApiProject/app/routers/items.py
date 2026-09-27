"""商品路由。"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import Pagination, require_login
from app.models import Item, User
from app.redis_client import redis_client
from app.schemas import ItemCreate, ItemOut, ItemUpdate

router = APIRouter(tags=["商品"])


def clear_items_cache():
    """清除商品列表缓存。"""
    for key in redis_client.scan_iter("items:list:*"):
        redis_client.delete(key)
    redis_client.delete("items:list")


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
    cache_key = f"items:list:{pagination.page}:{pagination.size}"
    cached = redis_client.get(cache_key)
    if cached is not None:
        redis_client.incr("stats:cache_hit")
        return json.loads(cached)
    redis_client.incr("stats:cache_miss")
    offset = (pagination.page - 1) * pagination.size
    items = db.query(Item).offset(offset).limit(pagination.size).all()
    redis_client.setex(
        cache_key,
        60,
        json.dumps(jsonable_encoder(items)),
    )
    return items


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
    clear_items_cache()
    return db_item


@router.get(
    "/items/cached",
    response_model=list[ItemOut],
    summary="商品列表缓存示例",
    description="先查 Redis，未命中再查 MySQL 并写入缓存 60 秒。",
)
def cached_items(db: Session = Depends(get_db)):
    """Cache Aside 模式：缓存商品列表。"""
    cache_key = "items:list"
    cached = redis_client.get(cache_key)
    if cached is not None:
        return json.loads(cached)
    items = db.query(Item).all()
    redis_client.setex(cache_key, 60, json.dumps(jsonable_encoder(items)))
    return items


@router.get(
    "/cache/stats",
    summary="缓存命中统计",
    description="返回 Redis 商品缓存命中/未命中次数。",
)
def cache_stats():
    """查看缓存命中统计。"""
    hits = int(redis_client.get("stats:cache_hit") or 0)
    misses = int(redis_client.get("stats:cache_miss") or 0)
    return {"hits": hits, "misses": misses}


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
    clear_items_cache()
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
    clear_items_cache()
