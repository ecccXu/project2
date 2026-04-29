# backend/models.py

import json
import logging
from datetime import datetime

from sqlalchemy import (
    Column, Integer, Float, String,
    Boolean, DateTime, Text, Index
)
from sqlalchemy.sql import func

from database import Base

logger = logging.getLogger("Models")


# ==========================================
# 表1：传感器实时数据表
#
# 设计说明：
#   - 数值型字段（温度/湿度等）使用String存储AES密文
#     明文数值在内存中使用，落库时加密，查询时解密展示
#   - 状态型字段（status/fault_code）明文存储
#     方便SQL直接按状态筛选，无需解密
#   - sensor_id 对应节点标识
#     模拟器：ENV_SIM_001 / ENV_SIM_002
#     ESP32硬件（预留）：ESP32_001
#   - is_abnormal 由 test_engine.run_content_test() 判定
#     每条数据入库时自动写入合规校验结果
# ==========================================
class SensorData(Base):
    __tablename__ = "sensor_data"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 节点标识（多节点支持的核心字段）
    # 模拟器和ESP32硬件共用此表，通过sensor_id区分
    sensor_id   = Column(String(64), nullable=False, index=True)

    # 数值型传感器数据：存储AES-CBC密文
    # 格式：Base64编码字符串（IV + 密文 + HMAC）
    # 最大长度估算：JSON数值明文<20字符，加密后Base64<128字符
    in_car_temp  = Column(String(256), nullable=True)   # 车内温度（℃）
    out_car_temp = Column(String(256), nullable=True)   # 车外温度（℃）
    humidity     = Column(String(256), nullable=True)   # 车内湿度（%）
    pm25         = Column(String(256), nullable=True)   # PM2.5（μg/m³）
    co2          = Column(String(256), nullable=True)   # CO2浓度（ppm）

    # 状态型数据：明文存储，便于SQL查询和统计
    status       = Column(String(32),  nullable=False, default="NORMAL")
    fault_code   = Column(String(64),  nullable=False, default="NONE")

    # 传输质量指标
    latency_ms   = Column(Integer, nullable=True, default=0)  # 端到端传输延迟（毫秒）

    # test_engine.run_content_test() 合规校验结果
    is_abnormal  = Column(Boolean,  nullable=False, default=False)  # 是否存在超标项
    error_msg    = Column(Text,     nullable=True)                  # 超标详情，正常时为空

    # 时间戳
    # server_time：数据到达后端的时间，用于历史查询排序
    server_time  = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow   # Windows兼容：不使用func.now()
    )

    # ==========================================
    # 联合索引：按节点+时间查历史数据的常见查询模式
    # 例如：查 ENV_SIM_001 最近1小时的数据
    # ==========================================
    __table_args__ = (
        Index('idx_sensor_time', 'sensor_id', 'server_time'),
    )

    def to_dict(self) -> dict:
        """
        转为字典（用于API返回）
        注意：数值字段返回的是密文，前端展示需要后端解密后再返回
        如需返回明文，请使用 to_display_dict()
        """
        return {
            "id":           self.id,
            "sensor_id":    self.sensor_id,
            "status":       self.status,
            "fault_code":   self.fault_code,
            "latency_ms":   self.latency_ms,
            "is_abnormal":  self.is_abnormal,
            "error_msg":    self.error_msg,
            "server_time":  self.server_time.strftime('%Y-%m-%d %H:%M:%S')
                            if self.server_time else None,
        }

    def __repr__(self) -> str:
        return (
            f"<SensorData id={self.id} "
            f"sensor_id={self.sensor_id} "
            f"status={self.status} "
            f"abnormal={self.is_abnormal}>"
        )


# ==========================================
# 表2：测试报告表
#
# 设计说明：
#   - 每次完整的测试套件执行结束后，生成一条报告记录
#   - details 存储每个用例的详细结果（JSON字符串）
#   - node_id 记录本次测试针对哪个节点
#     支持后续对比不同节点（模拟器 vs ESP32）的测试结果
#   - pass_rate 冗余存储，方便列表页直接展示，无需计算
# ==========================================
class TestReport(Base):
    __tablename__ = "test_reports"

    id           = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 报告基本信息
    report_name  = Column(String(128), nullable=False)   # 报告名称，例如"2024-01-15 14:30 测试报告"
    node_id      = Column(String(64),  nullable=False)   # 测试目标节点ID

    # 统计数据（冗余存储，避免每次从details计算）
    total_cases  = Column(Integer, nullable=False, default=0)   # 总用例数
    pass_count   = Column(Integer, nullable=False, default=0)   # 通过数
    fail_count   = Column(Integer, nullable=False, default=0)   # 失败数
    error_count  = Column(Integer, nullable=False, default=0)   # 错误数
    pass_rate    = Column(Float,   nullable=False, default=0.0) # 通过率（0.0~1.0）

    # 详细结果：存储 test_bench 返回的 results 列表（JSON序列化）
    # 格式示例：
    # [
    #   {
    #     "case_id": "case_temp_step",
    #     "case": "阶跃响应测试 (目标: 80℃)",
    #     "status": "PASS",
    #     "duration": 12.5,
    #     "details": ["动态响应良好 (超调: 0.8℃)"]
    #   },
    #   ...
    # ]
    details      = Column(Text, nullable=True)

    # 时间戳
    create_time  = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow   # Windows兼容写法
    )

    # 按节点建索引，方便查询某节点的历史报告
    __table_args__ = (
        Index('idx_report_node_time', 'node_id', 'create_time'),
    )

    def get_details_list(self) -> list:
        """
        将JSON字符串的details字段解析为列表
        安全解析，失败时返回空列表
        """
        if not self.details:
            return []
        try:
            return json.loads(self.details)
        except json.JSONDecodeError as e:
            logger.error(f"[Models] TestReport(id={self.id}) details解析失败: {e}")
            return []

    def to_dict(self) -> dict:
        """转为字典（用于API列表页返回）"""
        return {
            "id":          self.id,
            "report_name": self.report_name,
            "node_id":     self.node_id,
            "total_cases": self.total_cases,
            "pass_count":  self.pass_count,
            "fail_count":  self.fail_count,
            "error_count": self.error_count,
            "pass_rate":   round(self.pass_rate * 100, 1),  # 转为百分比，例如 85.7
            "create_time": self.create_time.strftime('%Y-%m-%d %H:%M:%S')
                           if self.create_time else None,
        }

    def to_detail_dict(self) -> dict:
        """转为字典（用于API详情页返回，包含完整details）"""
        base = self.to_dict()
        base["details"] = self.get_details_list()
        return base

    def __repr__(self) -> str:
        return (
            f"<TestReport id={self.id} "
            f"node={self.node_id} "
            f"pass={self.pass_count}/{self.total_cases}>"
        )


# ==========================================
# 自测代码
# Windows运行方式：
#   cd backend
#   python models.py
# # ==========================================
if __name__ == "__main__":
    import sys
    import os

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    logging.basicConfig(level=logging.INFO)

    print("=" * 50)
    print("models.py 自测")
    print("Windows环境")
    print("=" * 50)

    # ✅ 关键修复：
    # 直接从database导入engine和Base，
    # 此时models.py已经在执行中，SensorData和TestReport
    # 已经注册到Base.metadata，不需要再import models
    from database import engine, Base, SessionLocal, init_db

    # 测试1：建表
    print("\n【测试1】建表")
    init_db()   # 此时Base.metadata已有表信息，直接建表
    print("✅ 建表成功")

    # 测试2：写入SensorData
    print("\n【测试2】写入SensorData")
    db = SessionLocal()
    try:
        record = SensorData(
            sensor_id    = "ENV_SIM_001",
            in_car_temp  = "mock_encrypted_temp",
            out_car_temp = "mock_encrypted_out_temp",
            humidity     = "mock_encrypted_humidity",
            pm25         = "mock_encrypted_pm25",
            co2          = "mock_encrypted_co2",
            status       = "NORMAL",
            fault_code   = "NONE",
            latency_ms   = 12,
            is_abnormal  = False,
            error_msg    = None,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        print(f"写入记录: {record}")
        print(f"to_dict: {record.to_dict()}")
        print("✅ SensorData写入成功")

        # 测试3：写入TestReport
        print("\n【测试3】写入TestReport")
        details = [
            {
                "case_id": "case_temp_step",
                "case": "阶跃响应测试 (目标: 80℃)",
                "status": "PASS",
                "duration": 12.5,
                "details": ["动态响应良好 (超调: 0.8℃)"]
            },
            {
                "case_id": "case_aes_tamper",
                "case": "安全通信链路抗篡改测试",
                "status": "PASS",
                "duration": 0.1,
                "details": ["安全防线有效：成功拦截篡改数据"]
            }
        ]
        report = TestReport(
            report_name = "2024-01-15 14:30 测试报告",
            node_id     = "ENV_SIM_001",
            total_cases = 2,
            pass_count  = 2,
            fail_count  = 0,
            error_count = 0,
            pass_rate   = 1.0,
            details     = json.dumps(details, ensure_ascii=False),
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        print(f"写入报告: {report}")
        print(f"to_dict: {report.to_dict()}")
        print(f"get_details_list: {report.get_details_list()}")
        print("✅ TestReport写入成功")

        # 测试4：查询验证
        print("\n【测试4】查询验证")
        queried = db.query(SensorData).filter(
            SensorData.sensor_id == "ENV_SIM_001"
        ).first()
        assert queried is not None
        assert queried.sensor_id == "ENV_SIM_001"
        print(f"查询结果: {queried}")
        print("✅ 查询成功")

    except Exception as e:
        db.rollback()
        print(f"❌ 测试失败: {e}")
        raise
    finally:
        db.close()

    print("\n" + "=" * 50)
    print("全部自测通过 ✅")
    print("=" * 50)
