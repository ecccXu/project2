from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

# 创建数据库实例
db = SQLAlchemy()

class SystemStatus(db.Model):
    """
    系统状态表 - 存储系统运行状态相关信息
    """
    __tablename__ = 'system_status'
    
    id = db.Column(db.Integer, primary_key=True)
    system_status = db.Column(db.String(50), nullable=False)  # online/offline
    connected_sensors = db.Column(db.Integer, default=0)  # 已连接传感器数量
    test_pass_rate = db.Column(db.Float, default=0.0)  # 测试通过率
    today_test_count = db.Column(db.Integer, default=0)  # 今日测试总数
    mqtt_connection_status = db.Column(db.String(50), nullable=False)  # connected/disconnected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Sensor(db.Model):
    """
    传感器信息表
    """
    __tablename__ = 'sensors'
    
    id = db.Column(db.Integer, primary_key=True)
    sensor_id = db.Column(db.String(100), unique=True, nullable=False)  # 传感器ID，如DHT11-001
    type = db.Column(db.String(50), nullable=False)  # 传感器类型，如温湿度
    status = db.Column(db.String(20), default='stopped')  # running/stopped
    description = db.Column(db.Text)  # 传感器描述
    data_source = db.Column(db.String(20), default='simulation')  # simulation/real
    last_active_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SensorConfig(db.Model):
    """
    传感器配置表
    """
    __tablename__ = 'sensor_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    data_source = db.Column(db.String(20), default='simulation')  # 数据来源模式：simulation/real
    sample_rate = db.Column(db.Integer, default=2)  # 采集频率（秒）
    temperature_min = db.Column(db.Float, default=-40.0)  # 温度模拟范围最小值
    temperature_max = db.Column(db.Float, default=85.0)  # 温度模拟范围最大值
    humidity_min = db.Column(db.Float, default=0.0)  # 湿度模拟范围最小值
    humidity_max = db.Column(db.Float, default=100.0)  # 湿度模拟范围最大值
    mqtt_qos = db.Column(db.Integer, default=1)  # MQTT QoS级别
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MqttConfig(db.Model):
    """
    MQTT配置表
    """
    __tablename__ = 'mqtt_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    broker_host = db.Column(db.String(200), default='localhost')  # Broker地址
    broker_port = db.Column(db.Integer, default=1883)  # Broker端口
    client_id = db.Column(db.String(200))  # 客户端ID
    clean_session = db.Column(db.Boolean, default=True)  # Clean Session标识
    username = db.Column(db.String(100))  # 用户名（可选）
    password = db.Column(db.String(100))  # 密码（可选）
    subscribe_topic = db.Column(db.String(200), default='vehicle/sensor/data/+')  # 数据订阅主题
    publish_topic_template = db.Column(db.String(200), default='vehicle/test/command/{sensor_id}')  # 指令发布主题模板
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TestCase(db.Model):
    """
    测试用例表
    """
    __tablename__ = 'test_cases'
    
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.String(50), unique=True, nullable=False)  # 测试用例ID，如TC-001
    name = db.Column(db.String(200), nullable=False)  # 测试用例名称
    type = db.Column(db.String(50), nullable=False)  # 测试类型，如功能测试、协议测试
    description = db.Column(db.Text)  # 测试用例描述
    enabled = db.Column(db.Boolean, default=True)  # 是否启用
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TestResult(db.Model):
    """
    测试结果表
    """
    __tablename__ = 'test_results'
    
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.String(100), nullable=False)  # 测试任务ID
    sensor_id = db.Column(db.String(100), nullable=False)  # 传感器ID
    case_id = db.Column(db.String(50), nullable=False)  # 测试用例ID
    case_name = db.Column(db.String(200))  # 测试用例名称
    result = db.Column(db.String(20), nullable=False)  # pass/fail
    test_time = db.Column(db.DateTime, default=datetime.utcnow)  # 测试时间
    details = db.Column(db.Text)  # 测试详情
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SensorData(db.Model):
    """
    传感器原始数据表
    """
    __tablename__ = 'sensor_data'
    
    id = db.Column(db.Integer, primary_key=True)
    data_id = db.Column(db.String(100), unique=True, nullable=False)  # 数据ID
    sensor_id = db.Column(db.String(100), nullable=False)  # 传感器ID
    temperature = db.Column(db.Float)  # 温度值
    humidity = db.Column(db.Float)  # 湿度值
    receive_time = db.Column(db.DateTime, default=datetime.utcnow)  # 接收时间
    source = db.Column(db.String(20), default='simulation')  # 数据来源：simulation/real
    created_at = db.Column(db.DateTime, default=datetime.utcnow)