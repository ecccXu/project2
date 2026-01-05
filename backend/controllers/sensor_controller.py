"""
传感器管理控制器
"""
from flask import Blueprint, request, jsonify
from utils.response import success_response, error_response
from services.sensor_service import (
    get_sensor_list, add_sensor, delete_sensor, 
    update_sensor_status, get_sensor_config, update_sensor_config
)
from config.db_config import db
import re

# 创建蓝图
sensor_bp = Blueprint('sensor', __name__, url_prefix='/api/v1')

@sensor_bp.route('/sensors', methods=['GET'])
def get_sensors():
    """
    获取传感器列表
    """
    try:
        sensors = get_sensor_list()
        return success_response(data=sensors)
    except Exception as e:
        return error_response(message=str(e), code=500)

@sensor_bp.route('/sensors', methods=['POST'])
def create_sensor():
    """
    添加传感器
    """
    try:
        sensor_data = request.get_json()
        if not sensor_data:
            return error_response(message="请求体不能为空", code=400)
        
        required_fields = ['sensorId', 'type']
        for field in required_fields:
            if field not in sensor_data:
                return error_response(message=f"缺少必需字段: {field}", code=400)
        
        # 验证sensorId格式
        sensor_id = sensor_data['sensorId']
        if not re.match(r'^[A-Za-z0-9_-]+$', sensor_id):
            return error_response(message="传感器ID格式不正确，应只包含字母、数字、下划线和连字符", code=400)
        
        result = add_sensor(sensor_data)
        return success_response(data=result, message="传感器添加成功")
    except ValueError as e:
        return error_response(message=str(e), code=400)
    except Exception as e:
        db.session.rollback()
        return error_response(message=str(e), code=500)

@sensor_bp.route('/sensors/<sensor_id>', methods=['DELETE'])
def remove_sensor(sensor_id):
    """
    删除传感器
    """
    try:
        result = delete_sensor(sensor_id)
        return success_response(data=result, message="传感器删除成功")
    except ValueError as e:
        return error_response(message=str(e), code=400)
    except Exception as e:
        db.session.rollback()
        return error_response(message=str(e), code=500)

@sensor_bp.route('/sensors/<sensor_id>/status', methods=['PUT'])
def update_status(sensor_id):
    """
    更新传感器状态
    """
    try:
        status_data = request.get_json()
        if not status_data:
            return error_response(message="请求体不能为空", code=400)
        
        if 'status' not in status_data:
            return error_response(message="缺少status字段", code=400)
        
        if status_data['status'] not in ['running', 'stopped']:
            return error_response(message="状态值无效，应为 'running' 或 'stopped'", code=400)
        
        result = update_sensor_status(sensor_id, status_data)
        return success_response(data=result, message="传感器状态更新成功")
    except ValueError as e:
        return error_response(message=str(e), code=400)
    except Exception as e:
        db.session.rollback()
        return error_response(message=str(e), code=500)

@sensor_bp.route('/sensors/config', methods=['GET'])
def get_config():
    """
    获取传感器配置
    """
    try:
        config = get_sensor_config()
        return success_response(data=config)
    except Exception as e:
        return error_response(message=str(e), code=500)

@sensor_bp.route('/sensors/config', methods=['PUT'])
def update_config():
    """
    更新传感器配置
    """
    try:
        config_data = request.get_json()
        if not config_data:
            return error_response(message="请求体不能为空", code=400)
        
        update_sensor_config(config_data)
        return success_response(data={}, message="传感器配置更新成功")
    except ValueError as e:
        return error_response(message=str(e), code=400)
    except Exception as e:
        db.session.rollback()
        return error_response(message=str(e), code=500)