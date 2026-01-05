import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    """基础配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'hard-to-guess-string-for-security'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 数据库配置 - 默认使用SQLite进行开发测试
    DB_TYPE = os.environ.get('DB_TYPE') or 'sqlite'  # sqlite, mysql
    
    if DB_TYPE == 'sqlite':
        # 使用SQLite数据库（文件数据库，无需额外配置）
        SQLALCHEMY_DATABASE_URI = 'sqlite:///cariot_test.db'
    else:
        # MySQL数据库配置
        MYSQL_HOST = os.environ.get('MYSQL_HOST') or 'localhost'
        MYSQL_PORT = int(os.environ.get('MYSQL_PORT') or 3306)
        MYSQL_USER = os.environ.get('MYSQL_USER') or 'root'
        MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD') or 'password'
        MYSQL_DB = os.environ.get('MYSQL_DB') or 'cariot_test'
        
        # 构建数据库连接URL
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    
    # MQTT配置
    MQTT_BROKER_HOST = os.environ.get('MQTT_BROKER_HOST') or 'localhost'
    MQTT_BROKER_PORT = int(os.environ.get('MQTT_BROKER_PORT') or 1883)
    MQTT_CLIENT_ID = os.environ.get('MQTT_CLIENT_ID') or 'CarTest-Backend-Client'
    
    # API配置
    API_VERSION = 'v1'
    API_PREFIX = f'/api/{API_VERSION}'
    
    # 服务器配置
    HOST = os.environ.get('HOST') or '0.0.0.0'
    PORT = int(os.environ.get('PORT') or 5000)
    
    # 分页配置
    DEFAULT_PAGE_SIZE = int(os.environ.get('DEFAULT_PAGE_SIZE') or 10)
    MAX_PAGE_SIZE = int(os.environ.get('MAX_PAGE_SIZE') or 100)


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    if Config.DB_TYPE != 'sqlite':
        SQLALCHEMY_ECHO = True  # 开启SQL查询日志


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # 使用内存数据库进行测试


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}