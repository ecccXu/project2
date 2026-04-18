# backend/database.py

import os
import logging
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

logger = logging.getLogger("Database")

# ==========================================
# 数据库配置
# 优先从环境变量读取，方便后续迁移到其他数据库
# 例如切换PostgreSQL只需修改环境变量，代码不用动
#
# 设置环境变量方式：
#   Windows: set DATABASE_URL=sqlite:///./test_system.db
#   Linux:   export DATABASE_URL=sqlite:///./test_system.db
# ==========================================
SQLALCHEMY_DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'sqlite:///./test_system.db'
)

# ==========================================
# 引擎创建
# check_same_thread=False：
#   SQLite默认只允许创建它的线程访问
#   我们有MQTT线程和FastAPI线程同时访问，必须关闭此限制
# ==========================================
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False,  # 允许多线程访问
        "timeout": 10,               # 等待写锁超时时间（秒）
    },
    # 连接池配置
    pool_pre_ping=True,              # 每次使用连接前检查连接是否有效
)

# ==========================================
# WAL模式配置
# WAL(Write-Ahead Logging)：SQLite并发写入优化
#
# 默认模式问题：
#   写操作会锁定整个数据库，MQTT线程写库时
#   FastAPI线程查询会被阻塞，出现"database is locked"
#
# WAL模式优势：
#   读写可以并发进行，MQTT线程写库不影响API查询
#   对我们的场景（每2秒写一条+随时查询）非常合适
# ==========================================
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """
    每次建立新的数据库连接时自动执行
    开启WAL模式 + 外键约束
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")   # 开启WAL模式
    cursor.execute("PRAGMA foreign_keys=ON")    # 开启外键约束
    cursor.execute("PRAGMA synchronous=NORMAL") # 平衡性能和安全性
    cursor.close()
    logger.debug("[数据库] SQLite PRAGMA 配置完成（WAL模式已启用）")


# ==========================================
# 会话工厂
# autocommit=False：手动提交，保证事务完整性
# autoflush=False：关闭自动flush，防止意外的隐式写库
# ==========================================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ==========================================
# 模型基类
# 所有 models.py 中的表模型都继承自这个Base
# ==========================================
Base = declarative_base()


# ==========================================
# FastAPI 标准依赖注入函数
#
# 使用方式（在 main.py 的路由函数中）：
#
#   from database import get_db
#   from sqlalchemy.orm import Session
#   from fastapi import Depends
#
#   @app.get("/api/data/history")
#   def get_history(db: Session = Depends(get_db)):
#       records = db.query(SensorData).all()
#       return records
#
# 机制说明：
#   每个HTTP请求进来时，自动创建一个新的Session
#   请求处理完成后（无论成功还是异常），自动关闭Session
#   保证连接不泄漏
# ==========================================
def get_db() -> Generator:
    """
    数据库Session依赖注入生成器
    每个请求独立Session，请求结束自动释放
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        # 发生异常时回滚，保证数据一致性
        db.rollback()
        logger.error(f"[数据库] Session异常，已回滚: {e}")
        raise
    finally:
        db.close()


def init_db():
    """
    初始化数据库，创建所有表
    在 main.py 的 lifespan 启动事件中调用

    注意：必须在调用此函数之前导入所有models
    否则Base.metadata里没有表信息，建表会失败

    调用方式（main.py）：
        import models  # 触发模型注册，不能省略
        from database import init_db
        init_db()
    """
    # 这里的import必须保留
    # 触发models.py执行，让所有Model类注册到Base.metadata
    import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("[数据库] 数据表初始化完成")


# ==========================================
# 自测代码
# 运行: python database.py
# ==========================================
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 50)
    print("database.py 自测")
    print("=" * 50)

    # 测试1：引擎创建
    print("\n【测试1】引擎创建")
    print(f"数据库URL: {SQLALCHEMY_DATABASE_URL}")
    print("✅ 引擎创建成功")

    # 测试2：WAL模式验证
    print("\n【测试2】WAL模式验证")
    with engine.connect() as conn:
        result = conn.execute(
            __import__('sqlalchemy').text("PRAGMA journal_mode")
        )
        mode = result.fetchone()[0]
        assert mode == "wal", f"❌ WAL模式未生效，当前模式: {mode}"
        print(f"当前journal_mode: {mode}")
        print("✅ WAL模式已启用")

    # 测试3：Session创建和关闭
    print("\n【测试3】Session生命周期")
    db = SessionLocal()
    try:
        db.execute(__import__('sqlalchemy').text("SELECT 1"))
        print("✅ Session创建并查询成功")
    finally:
        db.close()
        print("✅ Session正常关闭")

    # 测试4：get_db生成器
    print("\n【测试4】get_db依赖注入生成器")
    gen = get_db()
    db = next(gen)
    print(f"✅ get_db返回Session: {type(db).__name__}")
    try:
        next(gen)
    except StopIteration:
        print("✅ Session已自动关闭")

    print("\n" + "=" * 50)
    print("全部自测通过 ✅")
    print("=" * 50)
