# sensor_simulator.py

import paho.mqtt.client as mqtt
import json
import time
import random
import math

# ================= 配置区域 =================
BROKER = "broker.emqx.io"  # 使用公共测试服务器
PORT = 1883
DEVICE_ID = "ESP32_SIM_01"
TOPIC = f"vehicle/{DEVICE_ID}/sensors/realtime"


# ===========================================

def on_connect(client, userdata, flags, rc):
    """
    连接回调函数
    rc: 0 表示连接成功
    """
    if rc == 0:
        print(f"✅ 成功连接到 MQTT Broker: {BROKER}")
    else:
        print(f"❌ 连接失败，错误码: {rc}")


def generate_sensor_data():
    """
    生成模拟传感器数据
    包含：温度、湿度、振动加速度
    """
    # 模拟基础温度 (正弦波动 + 随机噪声)
    base_temp = 25 + 3 * math.sin(time.time() / 10)
    temp = round(base_temp + random.uniform(-0.5, 0.5), 2)

    # 模拟基础湿度
    hum = round(60 + random.uniform(-5, 5), 2)

    # === 模拟异常场景 (10%概率) ===
    is_abnormal = False
    if random.random() < 0.1:
        temp = round(random.uniform(90, 110), 2)  # 模拟高温故障
        is_abnormal = True
        print("⚠️ [模拟] 生成异常高温数据！")

    # 封装标准 JSON 格式
    payload = {
        "device_id": DEVICE_ID,
        "timestamp": int(time.time()),
        "data": {
            "temperature": temp,
            "humidity": hum,
            "acc_x": round(random.uniform(-0.1, 0.1), 2),
            "acc_y": round(random.uniform(-0.1, 0.1), 2),
            "acc_z": round(9.8 + random.uniform(-0.1, 0.1), 2)
        },
        "status": {
            "wifi_rssi": random.randint(-60, -40)
        }
    }
    return payload, is_abnormal


def run_simulator():
    # 初始化客户端
    client = mqtt.Client(client_id=DEVICE_ID)
    client.on_connect = on_connect

    try:
        # 连接服务器
        print(f"🚀 正在连接 {BROKER}...")
        client.connect(BROKER, PORT, 60)

        # 启动后台循环线程
        client.loop_start()

        print(f"📤 开始发送数据到 Topic: {TOPIC}")
        print("-" * 30)

        while True:
            # 1. 获取数据
            payload, _ = generate_sensor_data()

            # 2. 发布消息
            client.publish(TOPIC, json.dumps(payload), qos=1)

            # 3. 本地打印日志
            print(f"Sent: Temp={payload['data']['temperature']}℃ | Hum={payload['data']['humidity']}%")

            # 4. 采样间隔
            time.sleep(2)

    except KeyboardInterrupt:
        client.loop_stop()
        print("\n🛑 模拟器已停止")
    except Exception as e:
        print(f"❌ 发生错误: {e}")


if __name__ == "__main__":
    run_simulator()