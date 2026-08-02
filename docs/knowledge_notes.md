# 第1-2周 补充知识点

> 适用范围：Phase 1（基础巩固 — 第1-2周）
> 说明：以下知识点是学习计划中列出、但在任务管理器项目中没有实际用到的，单独整理出来方便回头查阅。

---

## 一、继承

### 是什么

一个类从另一个类获得已有的属性和方法，并在其基础上增加或修改。

### 为什么用

- 复用代码，避免重复
- 建立层次关系

### 语法

```python
class Animal:
    def __init__(self, name):
        self.name = name
    def speak(self):
        return "..."

class Dog(Animal):
    def speak(self):
        return "汪汪"

dog = Dog("旺财")
print(dog.name, dog.speak())
```

### super() 调用父类方法

```python
class Dog(Animal):
    def __init__(self, name, breed):
        super().__init__(name)
        self.breed = breed
```

---

## 二、装饰器

### 是什么

不修改原函数代码的前提下，给函数增加额外功能。

### 例子：日志装饰器

```python
def log(func):
    def wrapper(*args, **kwargs):
        print(f"调用: {func.__name__}")
        return func(*args, **kwargs)
    return wrapper

@log
def add(a, b):
    return a + b

add(3, 5)
```

`@log` 等价于 `add = log(add)`。

### 应用场景

给命令加执行时间统计：

```python
import time
def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        cost = time.time() - start
        print(f"  耗时: {cost:.3f}秒")
        return result
    return wrapper
```

---

## 三、上下文管理器

### 是什么

用 `with` 语句自动管理资源的获取和释放。

### 典型用法

```python
with open("test.txt", "w") as f:
    f.write("Hello")
# 出了 with 块，文件自动关闭
```

### 自定义

```python
class Timer:
    def __enter__(self):
        self.start = time.time()
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cost = time.time() - self.start
        print(f"耗时: {self.cost:.3f}秒")

with Timer():
    sum(range(1000000))
```

---

## 四、生成器

### 是什么

按需生成值，用 `yield` 代替 `return`。

### 为什么用

- 省内存（处理大量数据时）
- 惰性计算

### 例子

```python
def count_up_to(n):
    i = 1
    while i <= n:
        yield i
        i += 1

for num in count_up_to(5):
    print(num)
```

### 生成器表达式

```python
squares = (x * x for x in range(10))  # 生成器
squares_list = [x * x for x in range(10)]  # 列表
```

### 应用场景：读大文件

```python
def read_lines(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            yield line.strip()
```

---

## 五、迭代器

### 是什么

实现了 `__iter__` 和 `__next__` 方法的对象。

### 关系

可迭代对象 -> __iter__() -> 迭代器 -> __next__() -> 依次取值

### 自定义迭代器

```python
class CountDown:
    def __init__(self, start):
        self.current = start
    def __iter__(self):
        return self
    def __next__(self):
        if self.current <= 0:
            raise StopIteration
        self.current -= 1
        return self.current + 1

for n in CountDown(3):
    print(n)
```

### 要点

- 生成器就是迭代器的一种
- for 循环底层就是在调 __next__()

---

## 六、异常处理

### 为什么用

- 避免程序因为一个错误整个崩溃
- 给用户友好提示

### 基本语法

```python
try:
    num = int(input("输入数字: "))
    result = 10 / num
except ValueError:
    print("输入的不是有效数字")
except ZeroDivisionError:
    print("不能除以零")
except Exception as e:
    print(f"未知错误: {e}")
else:
    print("没有异常时执行")
finally:
    print("无论是否异常都执行")
```

### 自定义异常

```python
class TaskNotFoundError(Exception):
    pass

raise TaskNotFoundError("任务不存在")
```

---

## 七、虚拟环境与依赖管理

### 为什么用

项目之间依赖隔离，互不冲突。

### 基本操作

```bash
python -m venv venv
venv\Scripts\activate    # Windows
source venv/bin/activate # macOS/Linux
deactivate
```

### requirements.txt

```bash
pip freeze > requirements.txt
pip install -r requirements.txt
```

记得把 `venv/` 加到 `.gitignore`。

---

## 八、Git 工作流进阶

### 分支

```bash
git branch                  # 查看分支
git checkout -b feature-x   # 创建并切换
git switch feature-x        # 切换（新版）
```

### 合并

```bash
git checkout main
git merge feature-x
```

### 推送分支到 GitHub

```bash
git push -u origin feature-x
```

### PR 流程

1. 推送分支到 GitHub
2. 在 GitHub 仓库页面点 Compare & pull request
3. Review 后 Merge

### 解决冲突

合并时提示冲突，文件里会出现标记：

```text
<<<<<<< HEAD
你的代码
=======
别人的代码
>>>>>>> branch-name
```

手动保留正确版本，删掉标记，然后：

```bash
git add .
git commit -m "解决冲突"
```
