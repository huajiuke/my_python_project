"""任务管理器 - CLI 入口"""
from datetime import datetime
import sys
import logging
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from task_manager.models import Task, Priority, TaskStatus
from task_manager.storage import TaskStorage

logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s | %(message)s",
)

class TaskNotFoundError(Exception):
    """自定义错误，任务未找到"""
    pass

class TaskManager:
    """任务管理器业务逻辑"""

    def __init__(self, storage: TaskStorage):
        self.storage = storage
        self.tasks = storage.load()

    def _save(self):
        self.storage.save(self.tasks)

    def add(self, title: str, description: str = "", priority: str = "medium",
            due_date: Optional[datetime] = None):
        """添加新任务"""
        prio_map = {"l": Priority.LOW, "m": Priority.MEDIUM,
                     "h": Priority.HIGH, "u": Priority.URGENT}
        prio = prio_map.get(priority[0].lower(), Priority.MEDIUM)
        task = Task(title, description, prio, due_date)
        self.tasks.append(task)
        self._save()
        due_str = ""
        if due_date:
            due_str = " 截止: " + due_date.strftime("%m-%d")
        print("  [{}] {}{}".format(task.id[:6], task.title, due_str))

    def list(self, show_all: bool = False):
        """列出任务"""
        if show_all:
            items = self.tasks
            header = "全部任务（{}个）".format(len(items))
        else:
            items = [t for t in self.tasks if t.status == TaskStatus.PENDING]
            header = "待办任务（{}个）".format(len(items))
        date_now = datetime.now().strftime("%Y-%m-%d %H:%M")
        print(f"--- {header} {date_now} ---")
        if not items:
            print("  （空）")
            return
        for task in items:
            print("  {}".format(task))

    def done(self, task_id: str):
        """标记为完成"""
        for task in self.tasks:
            if task.id.startswith(task_id):
                if task.status == TaskStatus.COMPLETED:
                    print("  任务 [{}] 已完成，无需重复操作".format(task.id[:6]))
                    return
                task.mark_completed()
                self._save()
                print("  [x] {} 已标记完成".format(task.title))
                return
        # print("  未找到ID以 {} 开头的任务".format(task_id))
        raise TaskNotFoundError(f"  未找到ID以 {task_id} 开头的任务")

    def delete(self, task_id: str):
        """删除任务"""
        for i, task in enumerate(self.tasks):
            if task.id.startswith(task_id):
                removed = self.tasks.pop(i)
                self._save()
                print("  已删除: {}".format(removed.title))
                return
        # print("  未找到ID以 {} 开头的任务".format(task_id))
        raise TaskNotFoundError(f"  未找到ID以 {task_id} 开头的任务")

    def clear_done(self):
        """清空已完成任务"""
        count = 0
        for i in range(len(self.tasks) - 1, -1, -1):
            if self.tasks[i].status == TaskStatus.COMPLETED:
                removed = self.tasks.pop(i)
                count += 1
                print("  已删除: {}".format(removed.title))
        self._save()
        if count == 0:
            print("  没有已完成的任务")


def parse_date(date_str: str) -> Optional[datetime]:
    """把 '2026-08-01' 转成 datetime 对象，格式不对就返回 None"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print("  日期格式错误，应为 YYYY-MM-DD，忽略截止日期")
        return None


def print_help():
    print("""用法:
  add <标题> [-d <描述>] [-p low|medium|high|urgent] [--due YYYY-MM-DD]     添加任务
  list [--all]                                                            列出任务
  done <id>                                                               标记完成
  del <id>                                                                删除任务
  clear                                                                   清除已完成任务
  help                                                                    显示帮助
  exit                                                                    退出
""")


def main():
    storage = TaskStorage()
    mgr = TaskManager(storage)

    print("任务管理器 v1.0  （输入 help 查看命令，exit 退出）")
    while True:
        try:
            raw = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not raw:
            continue

        parts = raw.split()
        cmd = parts[0].lower()

        if cmd == "exit":
            break
        elif cmd == "help":
            print_help()
        elif cmd == "add" and len(parts) >= 2:
            title = parts[1]
            desc = ""
            prio = "medium"
            due = None
            i = 2
            while i < len(parts):
                if parts[i] == "-d" and i + 1 < len(parts):
                    desc = parts[i + 1]
                    i += 2
                elif parts[i] == "-p" and i + 1 < len(parts):
                    prio = parts[i + 1]
                    i += 2
                elif parts[i] == "--due" and i + 1 < len(parts):
                    due = parse_date(parts[i + 1])
                    i += 2
                else:
                    i += 1
            mgr.add(title, desc, prio, due)
        elif cmd == "list":
            show_all = "--all" in parts
            mgr.list(show_all)
        elif cmd == "done" and len(parts) >= 2:
            # mgr.done(parts[1])
            try:
                mgr.done(parts[1])
            except TaskNotFoundError as e:
                print(e)
        elif cmd == "del" and len(parts) >= 2:
            # mgr.delete(parts[1])
            try:
                mgr.delete(parts[1])
            except TaskNotFoundError as e:
                print(e)
        elif cmd == "clear":
            mgr.clear_done()
        else:
            print("  未知命令，输入 help 查看用法")


if __name__ == "__main__":
    main()
