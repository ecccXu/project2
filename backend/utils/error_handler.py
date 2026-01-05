"""
错误处理模块
"""
from flask import jsonify
from utils.response import error_response
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def register_error_handlers(app):
    """
    注册错误处理器
    """
    @app.errorhandler(400)
    def bad_request(error):
        logger.error(f"Bad request: {error}")
        return error_response(message="请求参数错误", code=400)
    
    @app.errorhandler(401)
    def unauthorized(error):
        logger.error(f"Unauthorized: {error}")
        return error_response(message="未授权访问", code=401)
    
    @app.errorhandler(403)
    def forbidden(error):
        logger.error(f"Forbidden: {error}")
        return error_response(message="权限不足", code=403)
    
    @app.errorhandler(404)
    def not_found(error):
        logger.error(f"Resource not found: {error}")
        return error_response(message="资源不存在", code=404)
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        logger.error(f"Method not allowed: {error}")
        return error_response(message="请求方法不允许", code=405)
    
    @app.errorhandler(409)
    def conflict(error):
        logger.error(f"Resource conflict: {error}")
        return error_response(message="资源冲突", code=409)
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return error_response(message="服务器内部错误", code=500)
    
    # 处理自定义异常
    @app.errorhandler(ValueError)
    def handle_value_error(error):
        logger.error(f"Value error: {error}")
        # 检查是否是特定错误码
        error_msg = str(error)
        if "测试任务冲突" in error_msg:
            return error_response(message=error_msg, code=603)
        elif "MQTT连接失败" in error_msg:
            return error_response(message=error_msg, code=601)
        elif "传感器" in error_msg and "不存在" in error_msg:
            return error_response(message=error_msg, code=404)
        elif "参数错误" in error_msg or "格式不正确" in error_msg:
            return error_response(message=error_msg, code=400)
        else:
            return error_response(message=error_msg, code=400)
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        logger.error(f"Unhandled exception: {error}")
        return error_response(message="服务器内部错误", code=500)
