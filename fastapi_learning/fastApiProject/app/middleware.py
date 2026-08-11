"""FastAPI 中间件注册。"""

import logging
import time

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import CORS_ORIGINS

logger = logging.getLogger(__name__)


class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        cost = round((time.time() - start) * 1000, 2)
        response.headers["X-Process-Time"] = str(cost)
        logger.info("%s %s 耗时 %.2fms", request.method, request.url.path, cost)
        return response


def register_middlewares(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LogMiddleware)
