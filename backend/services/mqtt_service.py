"""
MQTT配置服务
"""
from models import MqttConfig
from config.db_config import db
import paho.mqtt.client as mqtt
import time


def get_mqtt_config():
    """
    获取MQTT配置
    """
    config = MqttConfig.query.order_by(MqttConfig.id.desc()).first()
    if not config:
        # 如果没有配置，返回默认配置
        config = MqttConfig(
            broker_host='localhost',
            broker_port=1883,
            client_id='CarTest-Web-Client-12345',
            clean_session=True,
            subscribe_topic='vehicle/sensor/data/+',
            publish_topic_template='vehicle/test/command/{sensor_id}'
        )
        db.session.add(config)
        db.session.commit()
    
    return {
        "brokerHost": config.broker_host,
        "brokerPort": config.broker_port,
        "clientId": config.client_id,
        "cleanSession": config.clean_session,
        "username": config.username or "",
        "password": config.password or "",
        "subscribeTopic": config.subscribe_topic,
        "publishTopicTemplate": config.publish_topic_template
    }


def update_mqtt_config(config_data):
    """
    更新MQTT配置
    """
    # 验证参数
    broker_port = config_data.get('brokerPort')
    if broker_port is not None:
        if not isinstance(broker_port, int) or broker_port < 1 or broker_port > 65535:
            raise ValueError("端口号必须是1-65535之间的整数")
    
    config = MqttConfig.query.order_by(MqttConfig.id.desc()).first()
    if not config:
        # 如果没有配置，创建新的配置
        config = MqttConfig()
        db.session.add(config)
    
    # 更新配置数据
    if 'brokerHost' in config_data:
        config.broker_host = config_data['brokerHost']
    if 'brokerPort' in config_data:
        config.broker_port = config_data['brokerPort']
    if 'clientId' in config_data:
        config.client_id = config_data['clientId']
    if 'cleanSession' in config_data:
        config.clean_session = config_data['cleanSession']
    if 'username' in config_data:
        config.username = config_data['username']
    if 'password' in config_data:
        config.password = config_data['password']
    if 'subscribeTopic' in config_data:
        config.subscribe_topic = config_data['subscribeTopic']
    
    db.session.commit()
    return {}


def test_mqtt_connection(config_data=None):
    """
    测试MQTT连接
    """
    # 如果没有提供配置，则使用数据库中的配置
    if not config_data:
        mqtt_config = get_mqtt_config()
    else:
        mqtt_config = config_data
    
    # 创建MQTT客户端
    client_id = mqtt_config.get('clientId', f"CarTest-Test-Client-{int(time.time())}")
    clean_session = mqtt_config.get('cleanSession', True)
    
    client = mqtt.Client(client_id, clean_session=clean_session)
    
    # 设置用户名密码（如果提供）
    username = mqtt_config.get('username')
    password = mqtt_config.get('password')
    if username and password:
        client.username_pw_set(username, password)
    
    try:
        # 记录开始时间用于计算响应时间
        start_time = time.time()
        
        # 连接到MQTT Broker
        broker_host = mqtt_config.get('brokerHost', 'localhost')
        broker_port = mqtt_config.get('brokerPort', 1883)
        client.connect(broker_host, broker_port, 60)
        
        # 启动网络循环
        client.loop_start()
        
        # 等待连接完成
        time.sleep(1)
        
        # 计算响应时间
        response_time = int((time.time() - start_time) * 1000)
        
        # 断开连接
        client.loop_stop()
        client.disconnect()
        
        return {
            "connected": True,
            "responseTime": response_time
        }
    except Exception as e:
        # 连接失败
        return {
            "connected": False,
            "responseTime": 0,
            "error": str(e)
        }