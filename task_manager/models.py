"""任务管理器 - 数据模型模块"""
import uuid
from datetime import datetime
from enum import Enum

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
                 priority: Priority = Priority.MEDIUM):
        self.id = uuid.uuid4().hex[:8]
        self.title = title
        self.description = description
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

    def mark_completed(self):
        """标记为已完成"""
        self.status = TaskStatus.COMPLETED
        self.updated_at = datetime.now()

    def __str__(self):
        done = self.status == TaskStatus.COMPLETED
        icon = "x" if done else " "
        return "[{}] {} | {} ({})".format(icon, self.id[:6], self.title, self.priority.value)

    def __repr__(self):
        return "Task(id={!r}, title={!r}, status={!r})".format(
            self.id, self.title, self.status.value)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

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
        return task
