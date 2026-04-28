# backend/db/models.py
"""
============================================================
db/models.py - SQLAlchemy 数据模型
============================================================
"""

import json
import logging
from datetime import datetime

from sqlalchemy import (
    Column, Integer, Float, String,
    Boolean, DateTime, Text, Index
)

from db.session import Base

logger = logging.getLogger("Models")


class SensorData(Base):
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sensor_id = Column(String(64), nullable=False, index=True)

    in_car_temp  = Column(String(256), nullable=True)
    out_car_temp = Column(String(256), nullable=True)
    humidity     = Column(String(256), nullable=True)
    pm25         = Column(String(256), nullable=True)
    co2          = Column(String(256), nullable=True)

    status     = Column(String(32), nullable=False, default="NORMAL")
    fault_code = Column(String(64), nullable=False, default="NONE")

    latency_ms = Column(Integer, nullable=True, default=0)

    is_abnormal = Column(Boolean, nullable=False, default=False)
    error_msg   = Column(Text, nullable=True)

    server_time = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    __table_args__ = (
        Index('idx_sensor_time', 'sensor_id', 'server_time'),
    )

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "sensor_id":   self.sensor_id,
            "status":      self.status,
            "fault_code":  self.fault_code,
            "latency_ms":  self.latency_ms,
            "is_abnormal": self.is_abnormal,
            "error_msg":   self.error_msg,
            "server_time": self.server_time.strftime('%Y-%m-%d %H:%M:%S')
                           if self.server_time else None,
        }

    def __repr__(self) -> str:
        return (
            f"<SensorData id={self.id} "
            f"sensor_id={self.sensor_id} "
            f"status={self.status} "
            f"abnormal={self.is_abnormal}>"
        )


class TestReport(Base):
    __tablename__ = "test_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    report_name = Column(String(128), nullable=False)
    node_id     = Column(String(64),  nullable=False)

    total_cases = Column(Integer, nullable=False, default=0)
    pass_count  = Column(Integer, nullable=False, default=0)
    fail_count  = Column(Integer, nullable=False, default=0)
    error_count = Column(Integer, nullable=False, default=0)
    pass_rate   = Column(Float,   nullable=False, default=0.0)

    details = Column(Text, nullable=True)

    create_time = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    __table_args__ = (
        Index('idx_report_node_time', 'node_id', 'create_time'),
    )

    def get_details_list(self) -> list:
        if not self.details:
            return []
        try:
            return json.loads(self.details)
        except json.JSONDecodeError as e:
            logger.error(f"[Models] TestReport(id={self.id}) details 解析失败: {e}")
            return []

    def to_dict(self) -> dict:
        return {
            "id":          self.id,
            "report_name": self.report_name,
            "node_id":     self.node_id,
            "total_cases": self.total_cases,
            "pass_count":  self.pass_count,
            "fail_count":  self.fail_count,
            "error_count": self.error_count,
            "pass_rate":   round(self.pass_rate * 100, 1),
            "create_time": self.create_time.strftime('%Y-%m-%d %H:%M:%S')
                           if self.create_time else None,
        }

    def to_detail_dict(self) -> dict:
        base = self.to_dict()
        base["details"] = self.get_details_list()
        return base

    def __repr__(self) -> str:
        return (
            f"<TestReport id={self.id} "
            f"node={self.node_id} "
            f"pass={self.pass_count}/{self.total_cases}>"
        )