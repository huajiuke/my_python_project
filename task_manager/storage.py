"""任务管理器 - JSON 持久化层"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TaskStorage:
    """用 JSON 文件保存/加载任务列表"""

    def __init__(self, filepath: str = "tasks.json"):
        self.filepath = Path(filepath)

    def save(self, tasks: list) -> None:
        """将 Task 列表写入 JSON 文件"""
        data = [task.to_dict() for task in tasks]
        self.filepath.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info("已保存 %d 个任务到 %s", len(tasks), self.filepath)

    def load(self) -> list:
        """从 JSON 文件读取并还原 Task 列表"""
        if not self.filepath.exists():
            logger.info("文件 %s 不存在，返回空列表", self.filepath)
            return []

        raw = self.filepath.read_text(encoding="utf-8")
        data = json.loads(raw)
        from task_manager.models import Task

        tasks = [Task.from_dict(item) for item in data]
        logger.info("从 %s 加载了 %d 个任务", self.filepath, len(tasks))
        return tasks
