# backend/models.py

from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base

class SensorData(Base):
    """
    传感器数据表模型
    """
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)

    # 类型为 String，长度大，足够容纳密文
    temperature = Column(String(100))
    humidity = Column(String(100))

    # 延迟字段
    latency = Column(Integer, default=0)  # 存储毫秒数

    # 测试结果
    is_abnormal = Column(Boolean, default=False)  # 测试结果：是否异常
    error_msg = Column(String, nullable=True)     # 异常原因
    create_time = Column(DateTime, default=func.now()) # 入库时间