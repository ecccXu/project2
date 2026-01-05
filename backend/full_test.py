"""
全面测试所有API端点
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

def test_all_endpoints():
    """
    测试所有API端点
    """
    base_url = "http://localhost:5000/api/v1"
    
    print("开始测试所有API端点...")
    
    # 1. 测试系统状态接口
    print("\n1. 测试系统状态接口...")
    try:
        response = requests.get(f"{base_url}/system/status")
        print(f"   GET /system/status - 状态码: {response.status_code}")
        print(f"   响应数据: {response.json()}")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 2. 测试传感器配置接口
    print("\n2. 测试传感器配置接口...")
    try:
        # 获取传感器配置
        response = requests.get(f"{base_url}/sensors/config")
        print(f"   GET /sensors/config - 状态码: {response.status_code}")
        print(f"   响应数据: {response.json()}")
        
        # 更新传感器配置
        config_data = {
            "dataSource": "simulation",
            "sampleRate": 3,
            "temperatureRange": {"min": -40, "max": 85},
            "humidityRange": {"min": 0, "max": 100},
            "mqttQos": 1
        }
        response = requests.put(f"{base_url}/sensors/config", json=config_data)
        print(f"   PUT /sensors/config - 状态码: {response.status_code}")
        print(f"   响应数据: {response.json()}")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 3. 测试传感器管理接口
    print("\n3. 测试传感器管理接口...")
    try:
        # 获取传感器列表
        response = requests.get(f"{base_url}/sensors")
        print(f"   GET /sensors - 状态码: {response.status_code}")
        print(f"   响应数据: {response.json()}")
        
        # 添加传感器
        sensor_data = {
            "sensorId": "DHT11-001",
            "type": "温湿度",
            "description": "车内温湿度传感器",
            "dataSource": "simulation"
        }
        response = requests.post(f"{base_url}/sensors", json=sensor_data)
        print(f"   POST /sensors - 状态码: {response.status_code}")
        print(f"   响应数据: {response.json()}")
        
        # 更新传感器状态
        status_data = {"status": "running"}
        response = requests.put(f"{base_url}/sensors/DHT11-001/status", json=status_data)
        print(f"   PUT /sensors/DHT11-001/status - 状态码: {response.status_code}")
        print(f"   响应数据: {response.json()}")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 4. 测试MQTT配置接口
    print("\n4. 测试MQTT配置接口...")
    try:
        # 获取MQTT配置
        response = requests.get(f"{base_url}/mqtt/config")
        print(f"   GET /mqtt/config - 状态码: {response.status_code}")
        print(f"   响应数据: {response.json()}")
        
        # 更新MQTT配置
        mqtt_config = {
            "brokerHost": "localhost",
            "brokerPort": 1883,
            "clientId": "CarTest-Web-Client-12345",
            "cleanSession": True,
            "username": "",
            "password": "",
            "subscribeTopic": "vehicle/sensor/data/+"
        }
        response = requests.put(f"{base_url}/mqtt/config", json=mqtt_config)
        print(f"   PUT /mqtt/config - 状态码: {response.status_code}")
        print(f"   响应数据: {response.json()}")
        
        # 测试MQTT连接
        response = requests.post(f"{base_url}/mqtt/test-connection", json=mqtt_config)
        print(f"   POST /mqtt/test-connection - 状态码: {response.status_code}")
        print(f"   响应数据: {response.json()}")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 5. 测试测试用例接口
    print("\n5. 测试测试用例接口...")
    try:
        response = requests.get(f"{base_url}/test-cases")
        print(f"   GET /test-cases - 状态码: {response.status_code}")
        print(f"   响应数据: {len(response.json().get('data', []))} 个测试用例")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 6. 测试测试执行接口
    print("\n6. 测试测试执行接口...")
    try:
        # 开始测试
        test_data = {
            "sensorId": "DHT11-001",
            "caseIds": ["TC-001", "TC-002"]
        }
        response = requests.post(f"{base_url}/tests/start", json=test_data)
        print(f"   POST /tests/start - 状态码: {response.status_code}")
        print(f"   响应数据: {response.json()}")
        
        # 获取实时测试结果
        time.sleep(2)  # 等待测试执行
        response = requests.get(f"{base_url}/tests/realtime-results")
        print(f"   GET /tests/realtime-results - 状态码: {response.status_code}")
        print(f"   响应数据: {len(response.json().get('data', []))} 条结果")
    except Exception as e:
        print(f"   错误: {e}")
    
    # 7. 测试数据查询接口
    print("\n7. 测试数据查询接口...")
    try:
        # 查询测试结果
        response = requests.get(f"{base_url}/data/test-results")
        print(f"   GET /data/test-results - 状态码: {response.status_code}")
        print(f"   响应数据: {response.json().get('data', {}).get('total', 0)} 条记录")
        
        # 查询传感器数据
        response = requests.get(f"{base_url}/data/sensor-data")
        print(f"   GET /data/sensor-data - 状态码: {response.status_code}")
        print(f"   响应数据: {response.json().get('data', {}).get('total', 0)} 条记录")
    except Exception as e:
        print(f"   错误: {e}")
    
    print("\n所有API端点测试完成！")

if __name__ == "__main__":
    # 在后台线程启动服务器
    server_thread = threading.Thread(target=start_server)
    server_thread.daemon = True
    server_thread.start()
    
    print("等待服务器启动...")
    time.sleep(3)  # 等待服务器启动
    
    # 执行测试
    test_all_endpoints()
    
    # 让服务器继续运行一段时间以便查看结果
    print("\n服务器将继续运行，请按 Ctrl+C 停止")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n服务器已停止")