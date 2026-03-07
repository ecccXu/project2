"""
全面测试后端接口是否符合接口文档规范
"""
import requests
import json
import time
from threading import Thread
from app import create_app
import threading

# 启动Flask应用
def start_server():
    app = create_app('development')
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def test_system_status():
    """测试系统状态接口"""
    print("1. 测试系统状态接口...")
    try:
        response = requests.get("http://localhost:5000/api/v1/system/status")
        print(f"   GET /system/status - 状态码: {response.status_code}")
        
        expected_keys = {"code", "message", "data"}
        response_keys = set(response.json().keys())
        if expected_keys == response_keys:
            print("   ✓ 响应格式正确")
        else:
            print(f"   ✗ 响应格式错误，期望: {expected_keys}, 实际: {response_keys}")
        
        data = response.json()["data"]
        expected_data_keys = {"systemStatus", "connectedSensors", "testPassRate", "todayTestCount", "mqttConnectionStatus"}
        data_keys = set(data.keys())
        if expected_data_keys.issubset(data_keys):
            print("   ✓ 数据字段完整")
        else:
            print(f"   ✗ 数据字段不完整，期望: {expected_data_keys}, 实际: {data_keys}")
        
        print(f"   响应数据: {response.json()}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

def test_sensor_management():
    """测试传感器管理接口"""
    print("\n2. 测试传感器管理接口...")
    
    # 获取传感器列表
    try:
        response = requests.get("http://localhost:5000/api/v1/sensors")
        print(f"   GET /sensors - 状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 添加传感器
    try:
        sensor_data = {
            "sensorId": "DHT11-001",
            "type": "温湿度",
            "description": "车内温湿度传感器",
            "dataSource": "simulation"
        }
        response = requests.post("http://localhost:5000/api/v1/sensors", json=sensor_data)
        print(f"   POST /sensors - 状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 更新传感器状态
    try:
        status_data = {
            "status": "running"
        }
        response = requests.put("http://localhost:5000/api/v1/sensors/DHT11-001/status", json=status_data)
        print(f"   PUT /sensors/DHT11-001/status - 状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 获取传感器配置
    try:
        response = requests.get("http://localhost:5000/api/v1/sensors/config")
        print(f"   GET /sensors/config - 状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 更新传感器配置
    try:
        config_data = {
            "dataSource": "simulation",
            "sampleRate": 3,
            "temperatureRange": {"min": -40, "max": 85},
            "humidityRange": {"min": 0, "max": 100},
            "mqttQos": 1
        }
        response = requests.put("http://localhost:5000/api/v1/sensors/config", json=config_data)
        print(f"   PUT /sensors/config - 状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

def test_mqtt_config():
    """测试MQTT配置接口"""
    print("\n3. 测试MQTT配置接口...")
    
    # 获取MQTT配置
    try:
        response = requests.get("http://localhost:5000/api/v1/mqtt/config")
        print(f"   GET /mqtt/config - 状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 更新MQTT配置
    try:
        mqtt_config = {
            "brokerHost": "localhost",
            "brokerPort": 1883,
            "clientId": "CarTest-Web-Client-12345",
            "cleanSession": True,
            "username": "",
            "password": "",
            "subscribeTopic": "vehicle/sensor/data/+"
        }
        response = requests.put("http://localhost:5000/api/v1/mqtt/config", json=mqtt_config)
        print(f"   PUT /mqtt/config - 状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 测试MQTT连接
    try:
        response = requests.post("http://localhost:5000/api/v1/mqtt/test-connection", json=mqtt_config)
        print(f"   POST /mqtt/test-connection - 状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

def test_test_cases():
    """测试测试用例接口"""
    print("\n4. 测试测试用例接口...")
    
    try:
        response = requests.get("http://localhost:5000/api/v1/test-cases")
        print(f"   GET /test-cases - 状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

def test_test_execution():
    """测试测试执行接口"""
    print("\n5. 测试测试执行接口...")
    
    # 开始测试
    try:
        test_data = {
            "sensorId": "DHT11-001",
            "caseIds": ["TC-001", "TC-002"]
        }
        response = requests.post("http://localhost:5000/api/v1/tests/start", json=test_data)
        print(f"   POST /tests/start - 状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 获取实时测试结果
    try:
        time.sleep(2)  # 等待测试执行
        response = requests.get("http://localhost:5000/api/v1/tests/realtime-results")
        print(f"   GET /tests/realtime-results - 状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

def test_data_query():
    """测试数据查询接口"""
    print("\n6. 测试数据查询接口...")
    
    # 查询历史测试结果
    try:
        response = requests.get("http://localhost:5000/api/v1/data/test-results")
        print(f"   GET /data/test-results - 状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")
    
    # 查询传感器数据
    try:
        response = requests.get("http://localhost:5000/api/v1/data/sensor-data")
        print(f"   GET /data/sensor-data - 状态码: {response.status_code}")
        print(f"   响应: {response.json()}")
    except Exception as e:
        print(f"   ✗ 错误: {e}")

def run_comprehensive_test():
    """运行全面测试"""
    print("开始全面测试后端接口...")
    
    test_system_status()
    test_sensor_management()
    test_mqtt_config()
    test_test_cases()
    test_test_execution()
    test_data_query()
    
    print("\n全面测试完成！")

if __name__ == "__main__":
    # 在后台线程启动服务器
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    print("等待服务器启动...")
    time.sleep(3)  # 等待服务器启动
    
    # 执行测试
    run_comprehensive_test()
    
    # 让服务器继续运行一段时间以便查看结果
    print("\n服务器将继续运行，请按 Ctrl+C 停止")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n服务器已停止")