"""第 6 周 - 第 2 步：FastAPI + SQLAlchemy 数据库连接层

你需要在 TODO 处补全代码。
参考：D:/13155/PythonLearn/bookmark_manager/database.py
"""

# 1. 从 sqlalchemy 导入 create_engine
# 2. 从 sqlalchemy.orm 导入 DeclarativeBase 和 sessionmaker
# TODO: 补全导入
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
# SQLite 连接地址，数据库文件会生成在当前目录
SQLALCHEMY_DATABASE_URL = "sqlite:///./fastapi.db"

# 3. 创建 engine
#    SQLite 单线程限制需要传 connect_args={"check_same_thread": False}
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False
)  # TODO: 补全 create_engine(...)

# 4. 创建 SessionLocal 会话工厂
SessionLocal = sessionmaker(bind=engine)  # TODO: 补全 sessionmaker(...)

# 5. ORM 模型统一基类
class Base(DeclarativeBase):
    pass


# 6. FastAPI 依赖注入函数
#    - 请求开始时创建 Session
#    - yield 给路由使用
#    - 请求结束后关闭 Session
def get_db():
    db = SessionLocal()  # TODO: 补全 SessionLocal()
    try:
        yield db
    finally:
        db.close()
