"""
Flask应用主入口
"""
from flask import Flask
from config import db, config
from utils.error_handler import register_error_handlers
from services.test_case_service import initialize_default_test_cases
import os


def create_app(config_name='default'):
    """
    创建Flask应用工厂函数
    """
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(config[config_name])
    
    # 初始化数据库
    db.init_app(app)
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册路由
    register_blueprints(app)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
        
        # 初始化默认测试用例
        initialize_default_test_cases()
    
    return app


def register_blueprints(app):
    """
    注册所有蓝图
    """
    from controllers.system_controller import system_bp
    from controllers.sensor_controller import sensor_bp
    from controllers.mqtt_controller import mqtt_bp
    from controllers.test_case_controller import test_case_bp
    from controllers.test_execution_controller import test_execution_bp
    from controllers.data_controller import data_bp
    
    app.register_blueprint(system_bp)
    app.register_blueprint(sensor_bp)
    app.register_blueprint(mqtt_bp)
    app.register_blueprint(test_case_bp)
    app.register_blueprint(test_execution_bp)
    app.register_blueprint(data_bp)


if __name__ == '__main__':
    # 获取配置环境，默认为开发环境
    env = os.environ.get('FLASK_ENV', 'development')
    app = create_app(config_name=env)
    
    # 启动应用
    app.run(
        host=config[env].HOST,
        port=config[env].PORT,
        debug=config[env].DEBUG
    )