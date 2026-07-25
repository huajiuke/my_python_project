"""任务管理器 - 数据模型模块"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional


class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"


class Task:
    """单个任务的数据模型"""

    def __init__(self, title: str, description: str = "",
                 priority: Priority = Priority.MEDIUM,
                 due_date: Optional[datetime] = None):
        self.id = uuid.uuid4().hex[:8]
        self.title = title
        self.description = description
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self.due_date = due_date  # None 表示未设置截止日期

    def mark_completed(self):
        """标记为已完成"""
        self.status = TaskStatus.COMPLETED
        self.updated_at = datetime.now()

    def __str__(self):
        done = self.status == TaskStatus.COMPLETED
        icon = "x" if done else " "
        base = "[{}] {} | {} ({})".format(icon, self.id[:6], self.title, self.priority.value)
        if self.due_date:
            base += " 截止: {}".format(self.due_date.strftime("%m-%d"))
        return base

    def __repr__(self):
        return "Task(id={!r}, title={!r}, status={!r})".format(
            self.id, self.title, self.status.value)

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        # due_date 为 None 时不写入 JSON，保持数据简洁
        if self.due_date:
            result["due_date"] = self.due_date.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: dict):
        task = cls(
            title=data["title"],
            description=data.get("description", ""),
            priority=Priority(data["priority"]),
        )
        task.id = data["id"]
        task.status = TaskStatus(data["status"])
        task.created_at = datetime.fromisoformat(data["created_at"])
        task.updated_at = datetime.fromisoformat(data["updated_at"])
        # due_date 可能不存在于旧的 JSON 数据中，用 get 防止报错
        if "due_date" in data and data["due_date"]:
            task.due_date = datetime.fromisoformat(data["due_date"])
        return task
