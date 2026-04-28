# backend/db/session.py
"""
============================================================
db/session.py - 数据库会话与连接管理
============================================================
"""

import logging
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

from config import settings

logger = logging.getLogger("Database")

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
        "timeout": 10,
    },
    pool_pre_ping=True,
    echo=settings.DB_ECHO,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.close()
    logger.debug("[数据库] SQLite PRAGMA 配置完成（WAL 模式已启用）")


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"[数据库] Session 异常，已回滚: {e}")
        raise
    finally:
        db.close()


def init_db():
    from db import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    logger.info("[数据库] 数据表初始化完成")


if __name__ == "__main__":
    from sqlalchemy import text
    logging.basicConfig(level=logging.DEBUG)

    print("=" * 50)
    print("db/session.py 自测")
    print("=" * 50)

    print(f"\n数据库 URL: {SQLALCHEMY_DATABASE_URL}")

    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA journal_mode"))
        mode = result.fetchone()[0]
        assert mode == "wal", f"❌ WAL 模式未生效: {mode}"
        print(f"✅ WAL 模式已启用")

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        print("✅ Session 测试通过")
    finally:
        db.close()

    print("\n全部自测通过 ✅")