# backend/database.py
"""
============================================================
⚠️ 兼容性转发文件（DEPRECATED）
内容已迁移到 db/session.py，本文件仅用于向后兼容。
============================================================
"""

from db.session import (
    SQLALCHEMY_DATABASE_URL,
    engine,
    SessionLocal,
    Base,
    get_db,
    init_db,
)

__all__ = [
    'SQLALCHEMY_DATABASE_URL',
    'engine',
    'SessionLocal',
    'Base',
    'get_db',
    'init_db',
]