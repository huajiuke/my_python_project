# Python 面试八股速查

> 面向后端开发岗面试，按高频考点整理，适合快速复习。

## 一、基础概念

### 1. 解释型语言
- Python 是解释型语言，不需要编译成机器码，由解释器逐行执行
- 实际流程：`.py` -> 字节码（`.pyc`）-> Python 虚拟机执行

### 2. 动态类型与鸭子类型
- 变量本身没有类型，对象才有类型
- 鸭子类型：只要对象有对应方法，不关心具体类型
```python
class Dog:
    def speak(self):
        return "汪汪"

def make_sound(obj):
    return obj.speak()
```

### 3. `__name__ == "__main__"`
- 直接运行模块时为 `"__main__"`
- 被 import 时为模块名
- 作用：让测试代码只在直接运行时执行

### 4. 可变对象与不可变对象
| 类型 | 可变 | 示例 |
|------|------|------|
| list | 是 | `[1, 2]` |
| dict | 是 | `{"a": 1}` |
| set | 是 | `{1, 2}` |
| str | 否 | `"abc"` |
| tuple | 否 | `(1, 2)` |
| int/float/bool | 否 | `1` |

### 5. 浅拷贝与深拷贝
```python
import copy

a = [[1, 2], 3]
b = copy.copy(a)      # 浅拷贝：外层新对象，内层 list 仍是同一个
c = copy.deepcopy(a)  # 深拷贝：所有层级都复制
```

### 6. `is` 与 `==`
- `==` 比较值是否相等
- `is` 比较是否是同一个对象（id 相同）
```python
a = [1, 2]
b = [1, 2]
a == b  # True
a is b  # False
```

### 7. 小整数缓存与字符串驻留
- 小整数 `-5 ~ 256` 会被缓存，`is` 可能为 True
- 短字符串可能被驻留，但不要依赖这种行为
- 面试重点：这是实现细节，代码中应使用 `==`

### 8. LEGB 作用域
- 查找顺序：Local -> Enclosing -> Global -> Built-in
- `global`：修改全局变量
- `nonlocal`：修改闭包外层变量

### 9. 闭包
- 内部函数引用外部函数变量，并且外部函数已经返回
- 典型陷阱：循环中创建闭包，变量是同一个
```python
funcs = []
for i in range(3):
    funcs.append(lambda: i)
print([f() for f in funcs])  # [2, 2, 2]
```

### 10. 装饰器
- 在不修改原函数代码的前提下增强函数
- 核心结构：
```python
import functools

def my_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print("before")
        result = func(*args, **kwargs)
        print("after")
        return result
    return wrapper
```
- 为什么用 `@functools.wraps`：保留原函数 `__name__`、`__doc__`

### 11. 迭代器、生成器、可迭代对象
- 可迭代对象：实现 `__iter__` 或支持下标，如 list、dict、str
- 迭代器：实现 `__iter__` 和 `__next__`
- 生成器：用 `yield` 的函数，节省内存
```python
def gen():
    for i in range(1000000):
        yield i
```
- 生成器只能迭代一次

### 12. 上下文管理器
- 用 `with` 自动管理资源
- 实现方式一：`__enter__` / `__exit__`
- 实现方式二：`@contextmanager`
```python
from contextlib import contextmanager

@contextmanager
def resource():
    print("open")
    try:
        yield
    finally:
        print("close")
```

### 13. 可变默认参数陷阱
```python
def add(item, items=[]):  # 错误
    items.append(item)
    return items

def add(item, items=None):  # 正确
    if items is None:
        items = []
    items.append(item)
    return items
```

### 14. `*args` 与 `**kwargs`
- `*args` 接收任意位置参数，得到 tuple
- `**kwargs` 接收任意关键字参数，得到 dict
- 解包时也使用：
```python
def func(a, b, c):
    return a + b + c

func(*[1, 2, 3])
func(**{"a": 1, "b": 2, "c": 3})
```

### 15. 异常处理
- 捕获异常顺序：子类在前，父类在后
- `try/except/else/finally`
- `else`：没有异常时执行
- `finally`：无论是否异常都会执行
- 不要裸 `except:`，至少写 `except Exception`

## 二、数据结构

### 1. list 与 tuple
- list 可变，tuple 不可变
- tuple 可以做 dict 的 key（内部只含不可变对象时）
- tuple 比 list 更轻量，适合固定结构

### 2. dict 底层原理
- 基于哈希表实现
- key 必须是可哈希对象
- 插入顺序从 Python 3.7 起被语言规范保证
- 查找、插入、删除平均 O(1)

### 3. set 与 dict
- set 可以看成只有 key 的 dict
- 去重、交集、并集、差集很方便
```python
a = {1, 2, 3}
b = {2, 3, 4}
a & b  # 交集 {2, 3}
a | b  # 并集 {1, 2, 3, 4}
```

### 4. 常见复杂度
| 操作 | 复杂度 |
|------|--------|
| list 尾部追加 | O(1) |
| list 头部插入/删除 | O(n) |
| dict/set 查找 | O(1) |
| 排序 sorted | O(n log n) |

### 5. collections 常用类
- `defaultdict`：缺失 key 自动创建默认值
- `Counter`：计数
- `deque`：双端队列
- `OrderedDict`：有序字典（现在 dict 本身有序）
- `namedtuple`：带字段名的 tuple

## 三、函数式与标准库

### 1. 常用内建函数
```python
list(zip([1, 2], ["a", "b"]))  # [(1, 'a'), (2, 'b')]
list(enumerate(["a", "b"]))    # [(0, 'a'), (1, 'b')]
any([True, False])             # True
all([True, False])             # False
```

### 2. map / filter / reduce
```python
list(map(lambda x: x * 2, [1, 2, 3]))
list(filter(lambda x: x > 1, [1, 2, 3]))

from functools import reduce
reduce(lambda a, b: a + b, [1, 2, 3])
```

### 3. sorted 与 key
```python
sorted([(2, "b"), (1, "a")], key=lambda x: x[0])
```

### 4. functools
- `functools.wraps`
- `functools.partial`：固定部分参数
- `functools.lru_cache`：函数缓存

### 5. itertools
- `chain`：合并多个可迭代对象
- `product`：笛卡尔积
- `permutations`：排列
- `combinations`：组合

## 四、面向对象

### 1. 类变量与实例变量
- 类变量所有实例共享
- 实例变量每个实例独立
```python
class A:
    count = 0  # 类变量

    def __init__(self):
        self.name = "x"  # 实例变量
```

### 2. classmethod / staticmethod / property
- `@classmethod`：第一个参数是 cls，不依赖实例
- `@staticmethod`：和普通函数一样，放在类里
- `@property`：把方法变成属性，可加校验
```python
class User:
    def __init__(self, age):
        self._age = age

    @property
    def age(self):
        return self._age

    @age.setter
    def age(self, value):
        if value < 0:
            raise ValueError("age cannot be negative")
        self._age = value
```

### 3. 继承与多态
- 子类继承父类属性和方法
- 可重写父类方法实现多态
- `super()` 调用父类方法

### 4. MRO 方法解析顺序
- 多继承时按 C3 线性化算法决定查找顺序
- 查看：`ClassName.__mro__`
- 菱形继承问题由 MRO 解决

### 5. 常用魔术方法
- `__init__` / `__new__`
- `__str__` / `__repr__`
- `__eq__` / `__hash__`
- `__len__` / `__getitem__`
- `__enter__` / `__exit__`
- `__call__`

### 6. dataclass
```python
from dataclasses import dataclass

@dataclass
class User:
    id: int
    name: str
```
- 自动生成 `__init__`、`__repr__`、`__eq__`

### 7. 抽象基类 ABC
```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self):
        pass
```

## 五、内存与垃圾回收

### 1. 引用计数
- Python 对象通过引用计数管理内存
- 引用为 0 时立即释放

### 2. 循环引用
- 两个对象互相引用，引用计数无法归零
- 由垃圾回收器检测并清理

### 3. 分代回收
- 对象分为 0/1/2 三代
- 新对象在年轻代，回收频率高
- 老对象进入老年代，回收频率低

### 4. GIL 全局解释器锁
- CPython 同一时刻只允许一个线程执行字节码
- 影响：CPU 密集任务多线程无法真正并行
- 解决：多进程 / 用 C 扩展释放 GIL / 异步 I/O

## 六、并发

### 1. 进程、线程、协程
| 维度 | 进程 | 线程 | 协程 |
|------|------|------|------|
| 资源开销 | 大 | 中 | 小 |
| 是否并行 | 可并行 | GIL 限制 | 单线程并发 |
| 适用 | CPU 密集 | I/O 密集（部分） | 大量 I/O |
| 切换方式 | 系统调度 | 系统调度 | 用户态主动切换 |

### 2. threading
```python
import threading

lock = threading.Lock()
lock.acquire()
try:
    pass
finally:
    lock.release()
```
- 更推荐 `with lock:` 写法

### 3. multiprocessing
- 每个进程有独立内存和解释器
- 通过 `Process`、`Pool` 使用
- 进程间通信常用 `Queue`、`Pipe`

### 4. asyncio
```python
import asyncio

async def main():
    await asyncio.sleep(1)

asyncio.run(main())
```
- 适合网络请求、数据库连接等 I/O 密集任务
- 不是让代码变快，而是减少等待时浪费

## 七、常见坑

1. 可变默认参数
2. 循环闭包延迟绑定
3. 字典遍历时修改
4. 浮点数精度
```python
0.1 + 0.2 == 0.3  # False
```
5. 链式赋值
```python
a = b = []
a.append(1)
# a 和 b 指向同一个 list
```
6. 用 `except:` 吞掉所有异常
7. 大列表直接 `+` 拼接，应该用 `extend` 或列表推导
8. 不理解深浅拷贝导致内层数据被修改

## 八、后端项目补充

### 1. FastAPI 高频
- 基于 Starlette 和 Pydantic
- 自动生成 OpenAPI/Swagger
- 依赖注入：`Depends`
- 同步路由用 `def`，异步路由用 `async def`
- `response_model` 过滤敏感字段

### 2. SQLAlchemy 高频
- Engine -> Session -> Query
- Session 不是线程安全对象
- 常见问题：N+1 查询
- 使用 `selectinload` / `joinedload` 预加载关系
- 生产环境用 Alembic 做迁移

### 3. JWT 高频
- Header.Payload.Signature
- 使用 `exp` 控制过期
- secret 放环境变量
- payload 不存密码

## 九、面试回答模板

问“讲一下 GIL”：
> GIL 是 CPython 的全局解释器锁，同一时刻只有一个线程能执行字节码。它保证了内存管理的线程安全，但也让 CPU 密集任务无法利用多核。I/O 密集任务可以继续用线程，因为等待 I/O 时会释放 GIL；CPU 密集任务建议用多进程。

问“装饰器是什么”：
> 装饰器是接收函数并返回新函数的可调用对象，用来在不修改原函数的情况下增强行为。核心是闭包，使用时最好加 `functools.wraps` 保留元信息。
