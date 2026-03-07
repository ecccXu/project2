"""
传感器管理服务
"""
from backend.models import Sensor, SensorConfig
from backend.config.db_config import db
from datetime import datetime
from sqlalchemy.exc import IntegrityError
import uuid
import re


def get_sensor_list():
    """
    获取传感器列表
    """
    sensors = Sensor.query.all()
    result = []
    for sensor in sensors:
        result.append({
            "sensorId": sensor.sensor_id,
            "type": sensor.type,
            "status": sensor.status,
            "lastActiveTime": sensor.last_active_time.isoformat() if sensor.last_active_time else None,
            "description": sensor.description,
            "dataSource": sensor.data_source
        })
    return result


def add_sensor(sensor_data):
    """
    添加传感器
    """
    # 验证传感器ID格式
    sensor_id = sensor_data.get('sensorId')
    if not sensor_id or not re.match(r'^[A-Za-z0-9_-]+$', sensor_id):
        raise ValueError("传感器ID格式不正确，应只包含字母、数字、下划线和连字符")
    
    # 检查传感器ID是否已存在
    existing_sensor = Sensor.query.filter_by(sensor_id=sensor_id).first()
    if existing_sensor:
        raise ValueError(f"传感器ID {sensor_id} 已存在")
    
    new_sensor = Sensor(
        sensor_id=sensor_id,
        type=sensor_data.get('type'),
        description=sensor_data.get('description', ''),
        data_source=sensor_data.get('dataSource', 'simulation')
    )
    
    try:
        db.session.add(new_sensor)
        db.session.commit()
        return {"sensorId": new_sensor.sensor_id}
    except IntegrityError:
        db.session.rollback()
        raise ValueError(f"传感器ID {sensor_id} 已存在")


def delete_sensor(sensor_id):
    """
    删除传感器
    """
    sensor = Sensor.query.filter_by(sensor_id=sensor_id).first()
    if not sensor:
        raise ValueError(f"传感器 {sensor_id} 不存在")
    
    # 检查传感器状态，只允许删除已停止的传感器
    if sensor.status == 'running':
        raise ValueError(f"无法删除正在运行的传感器 {sensor_id}，请先停止传感器")
    
    db.session.delete(sensor)
    db.session.commit()
    return {"sensorId": sensor_id}


def update_sensor_status(sensor_id, status_data):
    """
    更新传感器状态
    """
    sensor = Sensor.query.filter_by(sensor_id=sensor_id).first()
    if not sensor:
        raise ValueError(f"传感器 {sensor_id} 不存在")
    
    new_status = status_data.get('status')
    if new_status not in ['running', 'stopped']:
        raise ValueError("状态值无效，应为 'running' 或 'stopped'")
    
    sensor.status = new_status
    sensor.last_active_time = datetime.utcnow()
    db.session.commit()
    
    return {
        "sensorId": sensor.sensor_id,
        "status": sensor.status
    }


def get_sensor_config():
    """
    获取传感器配置
    """
    config = SensorConfig.query.order_by(SensorConfig.id.desc()).first()
    if not config:
        # 如果没有配置，返回默认配置
        config = SensorConfig(
            data_source='simulation',
            sample_rate=2,
            temperature_min=-40,
            temperature_max=85,
            humidity_min=0,
            humidity_max=100,
            mqtt_qos=1
        )
        db.session.add(config)
        db.session.commit()
    
    return {
        "dataSource": config.data_source,
        "sampleRate": config.sample_rate,
        "temperatureRange": {
            "min": config.temperature_min,
            "max": config.temperature_max
        },
        "humidityRange": {
            "min": config.humidity_min,
            "max": config.humidity_max
        },
        "mqttQos": config.mqtt_qos
    }


def update_sensor_config(config_data):
    """
    更新传感器配置
    """
    # 验证参数
    sample_rate = config_data.get('sampleRate')
    if sample_rate is not None:
        if not isinstance(sample_rate, int) or sample_rate < 1 or sample_rate > 10:
            raise ValueError("采集频率必须是1-10之间的整数")
    
    temp_range = config_data.get('temperatureRange', {})
    if 'min' in temp_range and 'max' in temp_range:
        if temp_range['min'] > temp_range['max']:
            raise ValueError("温度范围最小值不能大于最大值")
    
    hum_range = config_data.get('humidityRange', {})
    if 'min' in hum_range and 'max' in hum_range:
        if hum_range['min'] > hum_range['max'] or hum_range['min'] < 0 or hum_range['max'] > 100:
            raise ValueError("湿度范围应在0-100之间，且最小值不能大于最大值")
    
    mqtt_qos = config_data.get('mqttQos')
    if mqtt_qos is not None and mqtt_qos not in [0, 1, 2]:
        raise ValueError("MQTT QoS级别必须是0、1或2")
    
    config = SensorConfig.query.order_by(SensorConfig.id.desc()).first()
    if not config:
        # 如果没有配置，创建新的配置
        config = SensorConfig()
        db.session.add(config)
    
    # 更新配置数据
    if 'dataSource' in config_data:
        config.data_source = config_data['dataSource']
    if 'sampleRate' in config_data:
        config.sample_rate = config_data['sampleRate']
    
    # 更新温度范围
    if 'temperatureRange' in config_data:
        temp_range = config_data['temperatureRange']
        if 'min' in temp_range:
            config.temperature_min = temp_range['min']
        if 'max' in temp_range:
            config.temperature_max = temp_range['max']
    
    # 更新湿度范围
    if 'humidityRange' in config_data:
        hum_range = config_data['humidityRange']
        if 'min' in hum_range:
            config.humidity_min = hum_range['min']
        if 'max' in hum_range:
            config.humidity_max = hum_range['max']
    
    if 'mqttQos' in config_data:
        config.mqtt_qos = config_data['mqttQos']
    
    db.session.commit()
    return {}