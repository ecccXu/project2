"""
系统状态控制器
"""
from flask import Blueprint
from backend.utils.response import success_response
from backend.services.system_service import get_system_status

# 创建蓝图
system_bp = Blueprint('system', __name__, url_prefix='/api/v1')

@system_bp.route('/system/status', methods=['GET'])
def get_status():
    """
    获取系统整体状态
    """
    status_data = get_system_status()
    return success_response(data=status_data)