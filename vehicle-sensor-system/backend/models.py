# backend/models.py

from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime
from sqlalchemy.sql import func
from database import Base

class SensorData(Base):
    """
    车载环境传感器数据表模型
    """
    __tablename__ = "sensor_data"

    id = Column(Integer, primary_key=True, index=True)
    sensor_id = Column(String, index=True)

    # 数值型数据：类型为 String，用于存储 AES 密文
    in_car_temp = Column(String(100))    # 车内温度
    out_car_temp = Column(String(100))   # 车外温度
    humidity = Column(String(100))       # 车内湿度
    pm25 = Column(String(100))           # PM2.5
    co2 = Column(String(100))            # CO2浓度

    # 状态型数据：明文存储，方便数据库查询和统计
    status = Column(String, default="NORMAL")      # 传感器上报状态
    fault_code = Column(String, default="NONE")    # 传感器上报故障码

    # 延迟与测试结果
    latency = Column(Integer, default=0)           # 传输延迟(毫秒)
    is_abnormal = Column(Boolean, default=False)    # 后台测试引擎判定：是否异常
    error_msg = Column(String, nullable=True)       # 后台测试引擎判定：异常原因
    create_time = Column(DateTime, default=func.now())