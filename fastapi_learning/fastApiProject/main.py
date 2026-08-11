from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.middleware import register_middlewares
from app.routers import auth, files, items, users

STATIC_DIR = Path(__file__).resolve().parent / "app" / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


# 创建 FastAPI 实例
app = FastAPI(title="FastAPI 学习项目", lifespan=lifespan)

register_middlewares(app)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(items.router)
app.include_router(files.router)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get(
    "/",
    summary="首页",
    description="返回 Hello World 基础示例。",
)
async def root():
    """首页接口。"""
    return {"message": "Hello World"}


@app.get(
    "/hello/{name}",
    summary="问候接口",
    description="路径参数 name 示例。",
)
async def say_hello(name: str):
    """返回问候语。"""
    return {"message": f"Hello {name}"}
