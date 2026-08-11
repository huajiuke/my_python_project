from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

router = APIRouter(tags=["文件与响应"])
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@router.get(
    "/json",
    summary="返回JSON",
    description="演示 JSONResponse 返回 JSON 数据。",
)
async def get_json():
    """返回 JSON 响应。"""
    return JSONResponse({"msg": "这是JSON"})


@router.get(
    "/html",
    summary="返回HTML",
    description="演示 HTMLResponse 返回 HTML 页面。",
)
async def get_html():
    """返回 HTML 响应。"""
    return HTMLResponse("<h1>Hello FastAPI</h1>")


@router.get(
    "/file",
    summary="返回文件",
    description="演示 FileResponse，返回 static/hello.html 文件。",
)
async def get_file():
    """返回静态文件。"""
    return FileResponse(STATIC_DIR / "hello.html")


@router.get(
    "/redirect",
    summary="重定向",
    description="演示 RedirectResponse，跳转到首页 /。",
)
async def redirect():
    """重定向到首页。"""
    return RedirectResponse("/")


def send_email(to: str):
    print(f"send email to {to}")


@router.post(
    "/send",
    summary="发送通知（后台任务）",
    description="接收 email 表单字段，响应后执行后台邮件任务。",
)
async def send_notice(
    background_tasks: BackgroundTasks,
    email: str = Form(...),
):
    """把发邮件加入后台任务，立即返回受理结果。"""
    background_tasks.add_task(send_email, email)
    return {"message": "已受理"}


@router.post(
    "/upload",
    summary="上传文件",
    description="接收 username 表单字段和 file 文件，返回文件信息。",
)
async def upload(username: str = Form(...), file: UploadFile = File(...)):
    """读取上传文件并返回文件名和大小。"""
    content = await file.read()
    return {"username": username, "filename": file.filename, "size": len(content)}
