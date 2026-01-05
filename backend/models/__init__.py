"""
数据库模型模块初始化
"""
from config.db_config import db, SystemStatus, Sensor, SensorConfig, MqttConfig, TestCase, TestResult, SensorData

__all__ = ['db', 'SystemStatus', 'Sensor', 'SensorConfig', 'MqttConfig', 'TestCase', 'TestResult', 'SensorData']