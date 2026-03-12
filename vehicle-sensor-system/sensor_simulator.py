# sensor_simulator.py

import paho.mqtt.client as mqtt
import json
import time
import random
import math
from crypto_utils import encrypt_data  # 引入加密工具

# ================= 配置区域 =================
BROKER = "broker.emqx.io"
PORT = 1883
DEVICE_ID = "ESP32_SIM_01"
TOPIC = f"vehicle/{DEVICE_ID}/sensors/realtime"


# ===========================================

def on_connect(client, userdata, flags, rc, properties=None):
    """
    连接回调函数
    增加了 properties=None 参数以兼容新版本 paho-mqtt
    """
    if rc == 0:
        print(f"✅ 成功连接到 MQTT Broker: {BROKER}")
    else:
        print(f"❌ 连接失败，错误码: {rc}")


def generate_sensor_data():
    """
    生成模拟传感器数据
    【注意】这里必须只返回 data 字典，不要返回元组
    """
    # 模拟基础温度
    base_temp = 25 + 3 * math.sin(time.time() / 10)
    temp = round(base_temp + random.uniform(-0.5, 0.5), 2)
    hum = round(60 + random.uniform(-5, 5), 2)

    # 模拟异常场景
    if random.random() < 0.1:
        temp = round(random.uniform(90, 110), 2)
        print("⚠️ [模拟] 生成异常高温数据！")

    # 构造标准数据字典
    data = {
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

    # 【关键】确保这里只返回 data，不要返回其他变量
    return data


def run_simulator():
    # 兼容新版本 paho-mqtt (2.0+) 的初始化方式
    # 如果报错提示缺少 CallbackAPIVersion，请使用下面这行：
    # client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=DEVICE_ID)
    # 如果你的库版本较旧，使用下面这行：
    client = mqtt.Client(client_id=DEVICE_ID)

    client.on_connect = on_connect

    try:
        print(f"🚀 正在连接 {BROKER}...")
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        print(f"📤 开始发送【加密】数据到 Topic: {TOPIC}")
        print("-" * 30)

        while True:
            # 1. 获取数据 (这里是字典)
            payload_dict = generate_sensor_data()

            # 2. 转为 JSON 字符串
            json_str = json.dumps(payload_dict)

            # 3. 加密
            encrypted_payload = encrypt_data(json_str)

            if encrypted_payload:
                # 4. 发送
                client.publish(TOPIC, encrypted_payload, qos=1)

                # 打印日志
                temp = payload_dict['data']['temperature']
                print(f"Sent: 密文已发送 (原始温度: {temp}℃ )")
            else:
                print("加密失败")

            time.sleep(2)

    except KeyboardInterrupt:
        client.loop_stop()
        print("\n🛑 模拟器已停止")
    except Exception as e:
        print(f"❌ 发生错误: {e}")


if __name__ == "__main__":
    run_simulator()