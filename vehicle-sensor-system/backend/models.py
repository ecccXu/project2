# backend/models.py
"""
============================================================
⚠️ 兼容性转发文件（DEPRECATED）
内容已迁移到 db/models.py，本文件仅用于向后兼容。
============================================================
"""

from db.models import SensorData, TestReport

__all__ = ['SensorData', 'TestReport']