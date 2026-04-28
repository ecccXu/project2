# backend/config.py
"""
============================================================
config.py - 集中配置管理
============================================================

设计原则（12-Factor App）：
  - 所有可配置项集中在此文件
  - 支持通过环境变量覆盖默认值
  - 配置与代码分离，便于多环境部署

使用方式：
  from config import settings
  print(settings.MQTT_BROKER)

环境变量优先级：
  环境变量 > 代码默认值

支持的环境变量：
  - MQTT_BROKER          MQTT Broker 地址
  - MQTT_PORT            MQTT Broker 端口
  - AES_SECRET_KEY       AES 加密密钥（16/24/32 字节）
  - DATABASE_URL         数据库连接字符串
  - LOG_LEVEL            日志级别
============================================================
"""

import os
from pathlib import Path

# ==========================================
# 项目路径
# ==========================================
BASE_DIR = Path(__file__).resolve().parent


class Settings:
    """系统配置类（单例）"""

    # ==========================================
    # MQTT 配置
    # ==========================================
    MQTT_BROKER: str = os.environ.get('MQTT_BROKER', 'localhost')
    MQTT_PORT: int = int(os.environ.get('MQTT_PORT', '1883'))
    MQTT_KEEPALIVE: int = 60
    MQTT_CLIENT_ID: str = "VCAR_BACKEND"

    # MQTT 主题（与现有代码保持一致）
    MQTT_DATA_TOPIC: str = "vcar/sensors/+/data"        # 通配符订阅所有节点数据
    MQTT_CTRL_TOPIC: str = "vcar/sensors/+/control"     # 通配符订阅所有节点控制回显
    MQTT_CONTROL_TOPIC_TPL: str = "vcar/sensors/{node_id}/control"  # 下发指令模板

    # ==========================================
    # 加密配置
    # ⚠️ 重要：默认密钥必须与现有 crypto_utils.py 一致
    #         否则历史数据无法解密
    # ==========================================
    AES_SECRET_KEY: str = os.environ.get(
        'AES_SECRET_KEY',
        'VehicleTest2026!'  # 16字节默认密钥（与原 crypto_utils.py 一致）
    )

    # ==========================================
    # 数据库配置
    # ⚠️ 重要：保持与现有 database.py 一致的相对路径
    # ==========================================
    DATABASE_URL: str = os.environ.get(
        'DATABASE_URL',
        'sqlite:///./test_system.db'
    )
    DB_ECHO: bool = False  # 是否打印 SQL 日志

    # ==========================================
    # 日志配置
    # ==========================================
    LOG_LEVEL: str = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'

    # ==========================================
    # 节点池配置
    # ==========================================
    NODE_QUEUE_MAX_SIZE: int = 100   # 每个节点的滑动窗口大小

    # ==========================================
    # 测试合规校验阈值（默认值）
    # ==========================================
    DEFAULT_TEST_CONFIG: dict = {
        # 车内温度阈值（℃）
        "in_car_temp_min": 16.0,
        "in_car_temp_max": 32.0,

        # 车外温度阈值（℃）
        "out_car_temp_min": -20.0,
        "out_car_temp_max": 50.0,

        # 湿度阈值（%）
        "humidity_min": 20.0,
        "humidity_max": 80.0,

        # PM2.5 阈值（μg/m³），参考 GB 3095-2012
        "pm25_max": 75.0,

        # CO₂ 阈值（ppm），参考 GB/T 18883-2002
        "co2_max": 1000.0,
    }

    # ==========================================
    # FastAPI 应用配置
    # ==========================================
    APP_TITLE: str = "车载环境传感器自动化测试平台"
    APP_DESCRIPTION: str = (
        "基于 MQTT 协议的车载环境传感器自动化测试系统。\n"
        "支持多节点接入、实时监控、自动化测试、报告管理。"
    )
    APP_VERSION: str = "2.0.0"

    # CORS 配置
    CORS_ORIGINS: list = ["*"]  # 生产环境应限制具体域名
    CORS_METHODS: list = ["*"]
    CORS_HEADERS: list = ["*"]


# ==========================================
# 全局配置实例（单例模式）
# ==========================================
settings = Settings()


# ==========================================
# 启动时验证配置有效性
# ==========================================
def validate_config():
    """配置有效性校验，启动时调用"""
    # AES 密钥长度校验
    key_bytes = settings.AES_SECRET_KEY.encode('utf-8')
    assert len(key_bytes) in (16, 24, 32), (
        f"AES密钥长度必须为 16/24/32 字节，当前为 {len(key_bytes)} 字节，"
        f"请检查环境变量 AES_SECRET_KEY"
    )


# ==========================================
# 调试：启动时打印当前配置
# ==========================================
def print_config():
    """打印当前生效的配置（启动时调用，便于排查环境变量问题）"""
    print("=" * 60)
    print("📋 当前系统配置：")
    print("=" * 60)
    print(f"  MQTT Broker:    {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
    print(f"  MQTT 数据主题:  {settings.MQTT_DATA_TOPIC}")
    print(f"  数据库:         {settings.DATABASE_URL}")
    print(f"  日志级别:       {settings.LOG_LEVEL}")
    print(f"  AES密钥:        {'已配置 (' + str(len(settings.AES_SECRET_KEY.encode('utf-8'))) + ' 字节)' if settings.AES_SECRET_KEY else '未配置'}")
    print(f"  应用版本:       {settings.APP_VERSION}")
    print("=" * 60)


# 启动时自动验证
validate_config()


if __name__ == "__main__":
    # 直接运行此文件可以查看当前配置
    print_config()