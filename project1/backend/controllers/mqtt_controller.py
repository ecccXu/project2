"""
MQTT配置控制器
"""
from flask import Blueprint, request
from backend.utils.response import success_response, error_response
from backend.services.mqtt_service import get_mqtt_config, update_mqtt_config, test_mqtt_connection

# 创建蓝图
mqtt_bp = Blueprint('mqtt', __name__, url_prefix='/api/v1')

@mqtt_bp.route('/mqtt/config', methods=['GET'])
def get_config():
    """
    获取MQTT配置
    """
    try:
        config = get_mqtt_config()
        return success_response(data=config)
    except Exception as e:
        return error_response(message=str(e), code=500)

@mqtt_bp.route('/mqtt/config', methods=['PUT'])
def update_config():
    """
    更新MQTT配置
    """
    try:
        config_data = request.get_json()
        if not config_data:
            return error_response(message="请求体不能为空", code=400)
        
        update_mqtt_config(config_data)
        return success_response(data={}, message="MQTT配置更新成功")
    except Exception as e:
        return error_response(message=str(e), code=500)

@mqtt_bp.route('/mqtt/test-connection', methods=['POST'])
def test_connection():
    """
    测试MQTT连接
    """
    try:
        config_data = request.get_json()
        # 如果没有提供配置，使用当前配置进行测试
        result = test_mqtt_connection(config_data)
        
        if result['connected']:
            message = "MQTT连接测试成功"
            code = 200
        else:
            message = f"MQTT连接测试失败: {result.get('error', 'Unknown error')}"
            code = 601  # 自定义错误码
        
        return success_response(data=result, message=message)
    except Exception as e:
        return error_response(message=str(e), code=500)