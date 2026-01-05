"""
测试应用功能
"""
from app import create_app
from models import Sensor, SensorConfig, MqttConfig, TestCase, TestResult, SensorData
from config.db_config import db
import json
import requests
import time
import threading


def test_api_endpoints():
    """
    测试API端点
    """
    app = create_app('testing')  # 使用测试配置
    
    with app.app_context():
        # 创建所有表
        db.create_all()
        
        print("数据库表创建成功")
        
        # 测试数据插入
        # 添加一个传感器
        sensor = Sensor(
            sensor_id='DHT11-001',
            type='温湿度',
            description='车内温湿度传感器',
            data_source='simulation'
        )
        db.session.add(sensor)
        db.session.commit()
        
        print("传感器数据插入成功")
        
        # 测试获取传感器列表
        sensors = Sensor.query.all()
        print(f"获取到 {len(sensors)} 个传感器")
        
        return True


def run_app_for_manual_testing():
    """
    运行应用用于手动测试
    """
    app = create_app('development')
    
    # 在后台线程运行应用
    def run_server():
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    
    server_thread = threading.Thread(target=run_server)
    server_thread.daemon = True
    server_thread.start()
    
    print("应用已启动，正在监听端口 5000...")
    time.sleep(2)  # 等待服务器启动
    
    # 尝试访问API端点
    try:
        response = requests.get('http://localhost:5000/api/v1/system/status', timeout=5)
        if response.status_code == 200:
            print("API测试成功，系统状态:", response.json())
        else:
            print(f"API测试失败，状态码: {response.status_code}")
    except Exception as e:
        print(f"API测试异常: {e}")
    
    # 保持主线程运行一段时间以允许测试
    time.sleep(10)


if __name__ == "__main__":
    print("开始测试应用功能...")
    
    # 先进行基本功能测试
    success = test_api_endpoints()
    if success:
        print("基本功能测试通过")
        
        # 运行应用用于手动测试
        print("启动应用进行手动测试...")
        run_app_for_manual_testing()
    else:
        print("基本功能测试失败")