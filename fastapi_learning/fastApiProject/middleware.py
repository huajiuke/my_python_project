import time

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware


class LogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        cost = round((time.time() - start) * 1000, 2)
        response.headers["X-Process-Time"] = str(cost)
        print(f"{request.method} {request.url.path} 耗时 {cost}ms")
        return response


def register_middlewares(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LogMiddleware)
