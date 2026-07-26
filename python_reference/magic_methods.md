# 常用魔术方法速查表

---

## 分类总览

| 类别 | 方法 |
|------|------|
| 对象创建与表示 | `__init__` `__str__` `__repr__` `__del__` |
| 比较运算 | `__eq__` `__ne__` `__lt__` `__le__` `__gt__` `__ge__` `__hash__` |
| 数值运算 | `__add__` `__sub__` `__mul__` `__truediv__` `__floordiv__` `__mod__` |
| 容器操作 | `__len__` `__getitem__` `__setitem__` `__delitem__` `__contains__` `__iter__` `__next__` |
| with 语句 | `__enter__` `__exit__` |
| 可调用对象 | `__call__` |
| 属性访问 | `__getattr__` `__setattr__` `__delattr__` |

---

## 一、对象创建与表示

### `__init__(self, ...)`

创建对象时自动调用，初始化属性。

```python
class Task:
    def __init__(self, title, priority="medium"):
        self.title = title
        self.priority = priority
        self.done = False

t = Task("买菜")  # 自动调用 __init__
```

### `__str__(self)`

`print(obj)` 或 `str(obj)` 时调用。返回面向用户的易读字符串。

```python
class Task:
    def __str__(self):
        return f"[任务] {self.title} ({self.priority})"

print(Task("买菜"))  # [任务] 买菜 (medium)
```

### `__repr__(self)`

`repr(obj)` 或调试时调用。返回面向开发者的详细字符串，理想情况下应能通过 `eval()` 还原对象。

```python
class Task:
    def __repr__(self):
        return f"Task(title={self.title!r}, priority={self.priority!r})"

t = Task("买菜")
print(repr(t))  # Task(title='买菜', priority='medium')
```

**`!r` 的作用**：强制调用该参数的 `__repr__()` 而非 `__str__()`，保证字符串带引号、特殊字符被转义。

### `__del__(self)`

对象被垃圾回收时调用。**不推荐主动使用**，资源释放应通过上下文管理器。

---

## 二、比较运算

### `__eq__(self, other)`

`obj1 == obj2` 时调用。

```python
class Task:
    def __init__(self, task_id, title):
        self.id = task_id
        self.title = title

    def __eq__(self, other):
        if not isinstance(other, Task):
            return NotImplemented
        return self.id == other.id

t1 = Task(1, "买菜")
t2 = Task(1, "买菜")
t3 = Task(2, "健身")
print(t1 == t2)  # True
print(t1 == t3)  # False
```

### `__hash__(self)`

与 `__eq__` 配对使用。对象作为字典 key 或 set 元素时需要实现。

```python
class Task:
    def __hash__(self):
        return hash(self.id)

# 实现了 __eq__ 和 __hash__ 后才能放进 set
tasks = {Task(1, "买菜"), Task(2, "健身")}
```

**规则**：`__eq__` 返回 True 的两个对象，`__hash__` 必须相等。反过来说，如果重写了 `__eq__`，`__hash__` 默认被设为 None，对象就不能放进 set 或作为 dict key。

### 其他比较方法

| 方法 | 运算符 | 默认行为 |
|------|--------|----------|
| `__ne__(self, other)` | `!=` | 无 `__ne__` 时，返回 `not __eq__` |
| `__lt__(self, other)` | `<` | 无实现时报错 |
| `__le__(self, other)` | `<=` | 无实现时报错 |
| `__gt__(self, other)` | `>` | 无实现时报错 |
| `__ge__(self, other)` | `>=` | 无实现时报错 |

**@total_ordering 装饰器**：只需实现 `__eq__` 和其中一个比较方法，自动补全其余：

```python
from functools import total_ordering

@total_ordering
class Task:
    def __eq__(self, other):
        return self.priority == other.priority

    def __lt__(self, other):
        return self.priority < other.priority

# 自动获得 __le__、__gt__、__ge__
```

---

## 三、数值运算

### 基本运算

```python
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        return Point(self.x * scalar, self.y * scalar)

    def __str__(self):
        return f"({self.x}, {self.y})"

p1 = Point(1, 2)
p2 = Point(3, 4)
print(p1 + p2)  # (4, 6)
print(p2 - p1)  # (2, 2)
print(p1 * 3)   # (3, 6)
```

### 完整数值运算表

| 方法 | 运算符 | 反向运算 |
|------|--------|----------|
| `__add__` | `+` | `__radd__` |
| `__sub__` | `-` | `__rsub__` |
| `__mul__` | `*` | `__rmul__` |
| `__truediv__` | `/` | `__rtruediv__` |
| `__floordiv__` | `//` | `__rfloordiv__` |
| `__mod__` | `%` | `__rmod__` |
| `__pow__` | `**` | `__rpow__` |

**反向运算**：当 `a + b` 中 `a` 没有实现 `__add__` 或返回 `NotImplemented` 时，Python 会尝试 `b.__radd__(a)`。

---

## 四、容器操作

### `__len__(self)`

`len(obj)` 时调用。返回整数。

```python
class TaskList:
    def __init__(self):
        self._tasks = []

    def __len__(self):
        return len(self._tasks)

tl = TaskList()
print(len(tl))  # 0
```

### `__getitem__(self, key)`

`obj[key]` 时调用。

```python
class TaskList:
    def __getitem__(self, index):
        return self._tasks[index]

tl = TaskList()
# tl[0]  相当于  tl.__getitem__(0)
```

### `__setitem__(self, key, value)`

`obj[key] = value` 时调用。

```python
class TaskList:
    def __setitem__(self, index, task):
        self._tasks[index] = task
```

### `__delitem__(self, key)`

`del obj[key]` 时调用。

### `__contains__(self, item)`

`item in obj` 时调用。返回 bool。

```python
class TaskList:
    def __contains__(self, task):
        return task in self._tasks

# "买菜" in tl  相当于  tl.__contains__("买菜")
```

**注意**：没有实现 `__contains__` 时，Python 会退而使用 `__getitem__` 逐一尝试，但效率低很多。

### `__iter__(self)` 与 `__next__(self)`

使对象可被 `for` 循环遍历。

```python
class TaskList:
    def __iter__(self):
        self._index = 0
        return self

    def __next__(self):
        if self._index >= len(self._tasks):
            raise StopIteration
        task = self._tasks[self._index]
        self._index += 1
        return task

# for t in tl:  相当于不断调 __next__() 直到 StopIteration
```

---

## 五、with 语句

### `__enter__(self)` 与 `__exit__(self, exc_type, exc_val, exc_tb)`

```python
class Timer:
    def __enter__(self):
        self.start = __import__("time").time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        cost = __import__("time").time() - self.start
        print(f"耗时: {cost:.3f}秒")
        # 返回 True 吞掉异常，返回 False/None 继续抛出

with Timer():
    sum(range(1000000))
```

### `__exit__` 的参数

| 参数 | 类型 | 含义 |
|------|------|------|
| `exc_type` | `type` 或 `None` | 异常类型，无异常则为 None |
| `exc_val` | `Exception` 或 `None` | 异常实例 |
| `exc_tb` | `traceback` 或 `None` | 异常堆栈 |

---

## 六、可调用对象

### `__call__(self, ...)`

使对象可以像函数一样被调用。

```python
class Counter:
    def __init__(self):
        self.count = 0

    def __call__(self):
        self.count += 1
        return self.count

c = Counter()
print(c())  # 1  相当于 c.__call__()
print(c())  # 2
print(c())  # 3
```

**应用场景**：装饰器、策略模式、带状态的函数替代品。

---

## 七、属性访问

### `__getattr__(self, name)`

访问不存在的属性时调用。

```python
class DefaultConfig:
    def __getattr__(self, name):
        return f"配置 {name} 未设置"

cfg = DefaultConfig()
print(cfg.host)   # 配置 host 未设置
print(cfg.port)   # 配置 port 未设置
```

### `__setattr__(self, name, value)`

**任何**属性赋值时都调用。容易导致无限递归。

```python
class Task:
    def __setattr__(self, name, value):
        # 正确做法：调用父类的 __setattr__
        super().__setattr__(name, value)
        print(f"设置属性 {name} = {value!r}")

t = Task()
t.title = "买菜"  # 打印: 设置属性 title = '买菜'
```

**陷阱**：不要在 `__setattr__` 里写 `self.name = value`，这会再次调用 `__setattr__`，无限递归。必须用 `super().__setattr__()`。

### `__delattr__(self, name)`

`del obj.name` 时调用。

---

## 速查表：什么时候用哪个

| 需求 | 实现的魔术方法 |
|------|---------------|
| 控制对象初始化 | `__init__` |
| 打印友好信息 | `__str__` |
| 调试友好信息 | `__repr__` |
| 对象可比较 | `__eq__` + `__hash__` |
| 对象可排序 | `__lt__` + `@total_ordering` |
| 对象可做运算 | `__add__` / `__sub__` / `__mul__` 等 |
| 对象支持索引 | `__getitem__` / `__setitem__` |
| 对象可迭代 | `__iter__` / `__next__` |
| 对象可被 `in` 检查 | `__contains__` |
| 自定义 with 语句 | `__enter__` / `__exit__` |
| 对象可当函数用 | `__call__` |
| 自定义属性读写 | `__getattr__` / `__setattr__` |
