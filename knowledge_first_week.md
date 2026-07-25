    # 第1周 已学知识点（含代码样例）

> 对应项目：task_manager（命令行任务管理器）
> 目的：每个知识点附独立可运行的代码片段，方便回头复习

---

## 一、class 定义与对象实例化

### 核心语法

```python
class 类名:
    def __init__(self, 参数1, 参数2):
        self.属性1 = 参数1
        self.属性2 = 参数2

对象 = 类名(值1, 值2)
```

### 项目中的例子

```python
class Task:
    def __init__(self, title: str, description: str = "",
                 priority: Priority = Priority.MEDIUM):
        self.id = uuid.uuid4().hex[:8]
        self.title = title
        self.description = description
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

# 创建对象
task1 = Task("买菜")
task2 = Task("写周报", priority=Priority.HIGH)
```

### 自己试试

```python
class Student:
    def __init__(self, name: str, score: int = 0):
        self.name = name
        self.score = score

s1 = Student("张三", 85)
s2 = Student("李四")
print(s1.name, s1.score)  # 张三 85
print(s2.name, s2.score)  # 李四 0
```

### 要点

- `__init__` 是构造方法，创建对象时自动调用
- `self` 指向当前对象实例，所有实例方法的第一个参数都是 self
- `self.xxx = xxx` 将参数存为对象的属性

---

## 二、实例方法

### 是什么

定义在类里面、通过对象调用的函数。

### 项目中的例子

```python
class Task:
    def mark_completed(self):
        """标记为已完成"""
        self.status = TaskStatus.COMPLETED
        self.updated_at = datetime.now()

# 调用
task = Task("买菜")
print(task.status)        # PENDING
task.mark_completed()      # 调用方法
print(task.status)         # COMPLETED
```

### 自己试试

```python
class Counter:
    def __init__(self):
        self.count = 0

    def increment(self):
        self.count += 1

    def reset(self):
        self.count = 0

c = Counter()
c.increment()
c.increment()
print(c.count)  # 2
c.reset()
print(c.count)  # 0
```

### 要点

- 方法第一个参数必须是 `self`（名字是约定，但大家都这么写）
- 方法和普通函数的区别：方法要加 `self`，因为操作的是某个具体对象的数据

---

## 三、魔术方法（__str__ 与 __repr__）

### 是什么

双下划线开头结尾的方法，Python 在特定场景下自动调用。

### __str__：print 时显示的内容

```python
class Task:
    def __str__(self):
        done = self.status == TaskStatus.COMPLETED
        icon = "x" if done else " "
        return f"[{icon}] {self.id[:6]} | {self.title} ({self.priority.value})"

task = Task("买菜")
print(task)  # 自动调用 __str__，输出：[ ] a1b2c3 | 买菜 (medium)
```

### __repr__：调试时显示的内容

```python
class Task:
    def __repr__(self):
        return (f"Task(id={self.id!r}, title={self.title!r}, "
                f"status={self.status.value!r})")

task = Task("买菜")
print(repr(task))  # Task(id='a1b2c3d4', title='买菜', status='pending')
```

### 其他常用魔术方法

| 方法 | 触发时机 | 用途 |
|------|----------|------|
| `__len__` | `len(obj)` | 返回长度 |
| `__eq__` | `obj1 == obj2` | 比较相等 |
| `__lt__` | `obj1 < obj2` | 比较大小 |
| `__add__` | `obj1 + obj2` | 加法运算 |

### 自己试试

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __str__(self):
        return f"({self.x}, {self.y})"

    def __repr__(self):
        return f"Point(x={self.x}, y={self.y})"

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

p1 = Point(1, 2)
p2 = Point(3, 4)
print(p1)                   # (1, 2)
print(repr(p1))             # Point(x=1, y=2)
print(p1 + p2)              # (4, 6)
```

---

## 四、@classmethod 类方法

### 是什么

不通过实例、直接通过类调用的方法。第一个参数是 `cls`（类本身）而不是 `self`。

### 用途

- 提供另一种创建对象的方式（工厂方法）
- 操作类级别的数据

### 项目中的例子

```python
class Task:
    @classmethod
    def from_dict(cls, data: dict):
        """从字典还原 Task 对象"""
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

# 调用方式：不创建实例，直接通过类名调用
data = {"title": "买菜", "priority": "high", "status": "pending", ...}
task = Task.from_dict(data)
```

### 自己试试

```python
class Book:
    def __init__(self, title, author, pages):
        self.title = title
        self.author = author
        self.pages = pages

    @classmethod
    def from_csv_line(cls, line: str):
        """从 CSV 行创建 Book 对象"""
        parts = line.strip().split(",")
        return cls(title=parts[0], author=parts[1], pages=int(parts[2]))

    def __str__(self):
        return f"{self.title} - {self.author} ({self.pages}p)"

# 使用
line = "Python入门,张三,350"
book = Book.from_csv_line(line)
print(book)  # Python入门 - 张三 (350p)
```

### @staticmethod 静态方法的对比

```python
class MathUtils:
    @staticmethod
    def is_even(n: int) -> bool:
        return n % 2 == 0

# 调用
print(MathUtils.is_even(4))  # True
```

区别：`@staticmethod` 不需要 `cls` 参数，纯粹是把函数放在类的命名空间里。

---

## 五、Enum 枚举

### 是什么

把有限的几个选项定义成类型，而不是用字符串到处写死。

### 项目中的例子

```python
from enum import Enum

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class TaskStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"

# 使用
p = Priority.HIGH
print(p.value)       # "high"
print(p.name)        # "HIGH"

# 从字符串还原
p2 = Priority("medium")
print(p2)            # Priority.MEDIUM
```

### 不用枚举的坏处

```python
# 到处写字符串，容易写错
if task.priority == "hight":   # 拼写错误，不会报错
    do_something()

# 改用枚举，写错就报错
if task.priority == Priority.HIGHT:  # NameError，立即发现
    do_something()
```

### 自己试试

```python
class Color(Enum):
    RED = "#FF0000"
    GREEN = "#00FF00"
    BLUE = "#0000FF"

def paint(color: Color):
    print(f"用颜色 {color.value} 绘制")

paint(Color.RED)   # 用颜色 #FF0000 绘制
```

---

## 六、类型提示 (Type Hints)

### 是什么

给函数的参数和返回值标注类型，让代码更清晰，PyCharm 能自动补全和检查。

### 项目中的例子

```python
class Task:
    def __init__(self, title: str, description: str = "",
                 priority: Priority = Priority.MEDIUM):
        ...

    def to_dict(self) -> dict:
        ...

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        ...

class JsonStorage:
    def save(self, tasks: list) -> None:
        ...

    def load(self) -> list:
        ...
```

### 常用类型提示

```python
name: str = "张三"
age: int = 25
price: float = 99.8
is_active: bool = True
tags: list[str] = ["Python", "后端"]
info: dict[str, int] = {"age": 25, "score": 90}
maybe: Optional[str] = None   # 或 str | None（Python 3.10+）
```

### 注意

- 类型提示只是提示，不会在运行时强制检查
- 但 PyCharm 会根据提示给你代码补全和错误提醒
- 面试时写类型提示是加分项

---

## 七、if __name__ == "__main__" 入口惯用法

### 是什么

只有直接运行这个文件时才执行，被别的文件 import 时不执行。

### 项目中的例子

```python
if __name__ == "__main__":
    main()
```

### 为什么这么做

```python
# utils.py
def add(a, b):
    return a + b

# 如果不加 if 判断，别人 import utils 时会直接打印这句话
print("utils 被加载了")

# 正确的做法
if __name__ == "__main__":
    print("只有当 python utils.py 时才执行")
```

---

## 八、包与模块组织

### 是什么

把代码拆到不同文件里，用文件夹和 `__init__.py` 组织。

### 项目结构

```
task_manager/
├── __init__.py      # 空文件，告诉 Python 这是个包
├── __main__.py      # 入口文件
├── models.py        # 数据模型
└── storage.py       # 持久化
```

### 导入方式

```python
# 从包导入模块
from task_manager.models import Task
from task_manager.storage import TaskStorage

# 或者
import task_manager.models
task = task_manager.models.Task("买菜")
```

### python -m 运行

```bash
# 注意不是 python task_manager.py
python -m task_manager
```

`-m` 告诉 Python 以模块方式运行，会找包里的 `__main__.py`。

---

## 九、JSON 序列化 / 反序列化

### 是什么

把对象转为可存储的字典（序列化），再从字典还原成对象（反序列化）。

### 项目中的模式

```python
# 对象 -> 字典
def to_dict(self) -> dict:
    return {
        "id": self.id,
        "title": self.title,
        "priority": self.priority.value,
        "created_at": self.created_at.isoformat(),
    }

# 字典 -> 对象（类方法）
@classmethod
def from_dict(cls, data: dict):
    task = cls(title=data["title"], priority=Priority(data["priority"]))
    task.id = data["id"]
    task.created_at = datetime.fromisoformat(data["created_at"])
    return task
```

### 序列化到文件

```python
import json

# 写入
data = [task.to_dict() for task in tasks]
json.dump(data, open("tasks.json", "w", encoding="utf-8"), indent=2)

# 读取
data = json.load(open("tasks.json", "r", encoding="utf-8"))
tasks = [Task.from_dict(item) for item in data]
```

### 自己试试

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def to_dict(self):
        return {"name": self.name, "age": self.age}

    @classmethod
    def from_dict(cls, data):
        return cls(data["name"], data["age"])

# 测试
p = Person("张三", 25)
d = p.to_dict()
p2 = Person.from_dict(d)
print(p2.name, p2.age)  # 张三 25
```

---

## 十、列表推导式与过滤

### 是什么

用一行表达式快速生成或过滤列表。

### 项目中的例子

```python
# 过滤出未完成的任务
pending = [t for t in self.tasks if t.status == TaskStatus.PENDING]

# 全部转成字典
all_dicts = [task.to_dict() for task in tasks]
```

### 各种变形

```python
numbers = [1, 2, 3, 4, 5]

# 过滤：偶数
evens = [n for n in numbers if n % 2 == 0]      # [2, 4]

# 变换：每个数平方
squares = [n * n for n in numbers]               # [1, 4, 9, 16, 25]

# 过滤+变换：偶数的平方
even_squares = [n * n for n in numbers if n % 2 == 0]  # [4, 16]

# 字典推导式
square_dict = {n: n * n for n in numbers}
# {1: 1, 2: 4, 3: 9, 4: 16, 5: 25}
```

---

## 十一、日志 logging 基础

### 是什么

用 logging 模块代替 print，可以控制日志级别、输出到文件等。

### 项目中的用法

```python
import logging

logger = logging.getLogger(__name__)

# 配置（通常在入口文件设置一次）
logging.basicConfig(level=logging.WARNING, format="%(levelname)s | %(message)s")

# 使用
logger.info("已保存 %d 个任务", len(tasks))
logger.warning("文件不存在")
logger.error("写入失败")
```

### 日志级别（由低到高）

| 级别 | 数值 | 用途 |
|------|------|------|
| DEBUG | 10 | 调试信息 |
| INFO | 20 | 正常操作信息 |
| WARNING | 30 | 警告，不影响运行 |
| ERROR | 40 | 错误，功能受影响 |
| CRITICAL | 50 | 严重错误，可能崩溃 |

### print 与 logging 的选择

```python
# 临时调试：print 够了
print(f"task id = {task.id}")

# 生产环境：用 logging，可以控制输出级别和去向
logger.info("用户 %s 创建了任务 %s", user, task.id)
```

---

## 十二、f-string 与 .format() 字符串格式化

### f-string（Python 3.6+）

```python
name = "张三"
age = 25

# 直接嵌入变量
print(f"姓名: {name}, 年龄: {age}")

# 表达式
print(f"明年 {age + 1} 岁")

# 调用方法
print(f"大写: {name.upper()}")
```

### .format()

```python
# 项目中使用
header = "待办任务（{}个）".format(len(items))
print("  [{}] {}".format(task.id[:6], task.title))

# 位置参数
print("{} 今年 {} 岁".format("张三", 25))

# 按位置索引
print("{1} 是 {0} 的学生".format("老师", "张三"))

# 命名参数
print("{name} 今年 {age} 岁".format(name="张三", age=25))
```

---

## 十三、uuid 生成唯一标识

```python
import uuid

# 生成 32 位十六进制 ID
uid = uuid.uuid4().hex         # "a1b2c3d4e5f6..."

# 取前 8 位做短 ID
short_id = uuid.uuid4().hex[:8]  # "a1b2c3d4"
```

### 自己试试

```python
import uuid

class User:
    def __init__(self, name):
        self.id = uuid.uuid4().hex[:8]
        self.name = name

u1 = User("张三")
u2 = User("李四")
print(u1.id, u2.id)  # 各不相同
```

---

## 十四、datetime 时间处理

```python
from datetime import datetime

# 当前时间
now = datetime.now()

# 格式化输出
now.strftime("%Y-%m-%d %H:%M")       # "2026-07-25 14:30"
now.strftime("%Y年%m月%d日")          # "2026年07月25日"

# 从字符串解析
dt = datetime.fromisoformat("2026-07-25T14:30:00")

# ISO 格式输出
dt.isoformat()  # "2026-07-25T14:30:00"
```

---

## 十五、pathlib 文件路径操作

```python
from pathlib import Path

# 创建路径对象
p = Path("tasks.json")

# 检查存在
p.exists()       # True / False

# 读写文本
p.write_text("Hello", encoding="utf-8")
content = p.read_text(encoding="utf-8")

# 路径操作
Path(__file__).resolve().parent          # 当前文件所在目录
Path(__file__).resolve().parent.parent   # 上一级目录
```

---

## 十六、综合练习：把你学的串起来

下面的示例把本章大部分知识点合并到一个文件里：

```python
"""综合示例：简单的书籍管理器"""
import uuid
import json
from datetime import datetime
from enum import Enum
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


class Category(Enum):
    """图书分类"""
    TECH = "技术"
    NOVEL = "小说"
    OTHER = "其他"


class Book:
    """图书模型"""

    def __init__(self, title: str, author: str,
                 category: Category = Category.OTHER):
        self.id = uuid.uuid4().hex[:8]
        self.title = title
        self.author = author
        self.category = category
        self.created_at = datetime.now()

    def __str__(self):
        return f"[{self.id[:6]}] {self.title} - {self.author}"

    def __repr__(self):
        return f"Book(id={self.id!r}, title={self.title!r})"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "category": self.category.value,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict):
        book = cls(
            title=data["title"],
            author=data["author"],
            category=Category(data["category"]),
        )
        book.id = data["id"]
        book.created_at = datetime.fromisoformat(data["created_at"])
        return book


class BookStorage:
    """JSON 文件存储"""

    def __init__(self, filepath: str = "books.json"):
        self.filepath = Path(filepath)

    def save(self, books: list[Book]) -> None:
        data = [b.to_dict() for b in books]
        self.filepath.write_text(
            json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        logger.info("已保存 %d 本书", len(books))

    def load(self) -> list[Book]:
        if not self.filepath.exists():
            return []
        data = json.loads(self.filepath.read_text(encoding="utf-8"))
        return [Book.from_dict(item) for item in data]


def main():
    storage = BookStorage()
    books = storage.load()

    while True:
        cmd = input("> ").strip()
        if cmd == "exit":
            break
        elif cmd.startswith("add"):
            parts = cmd.split(maxsplit=2)
            if len(parts) >= 3:
                book = Book(title=parts[1], author=parts[2])
                books.append(book)
                storage.save(books)
                print(f"  添加: {book}")
        elif cmd == "list":
            for b in books:
                print(f"  {b}")
            print(f"  共 {len(books)} 本")


if __name__ == "__main__":
    main()
```
