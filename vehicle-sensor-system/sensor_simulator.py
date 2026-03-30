# sensor_simulator.py

import paho.mqtt.client as mqtt
import json
import time
import random
import math
from crypto_utils import encrypt_data

# ================= 配置区域 =================
# 测试时可以使用公共服务器，如果你在本地跑，可以改为 127.0.0.1
BROKER = "broker.emqx.io"
PORT = 1883
TOPIC_DATA = "vcar/sensors/environment/data"
TOPIC_CONTROL = "vcar/sensors/environment/control"


# ===========================================


class CarEnvironmentSimulator:
    def __init__(self, broker_ip, port=1883):
        self.broker_ip = broker_ip
        self.port = port

        # 传感器真实物理状态 (带惯性)
        self.state = {
            "in_car_temp": 25.0,
            "out_car_temp": 25.0,
            "humidity": 50.0,
            "pm25": 20.0,
            "co2": 400.0
        }

        # 目标值 (工况切换时改变目标，物理状态会慢慢逼近目标)
        self.targets = self.state.copy()

        # 故障与状态
        self.status = "NORMAL"
        self.fault_code = "NONE"
        self.overrides = {}  # 手动强制覆盖的值

        # MQTT客户端
        self.client = mqtt.Client(client_id="EnvSimulator_001")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"[INFO] 成功连接到 MQTT Broker: {self.broker_ip}")
            # 连接成功后，订阅下行控制主题
            client.subscribe(TOPIC_CONTROL)
            print(f"[INFO] 已订阅控制主题: {TOPIC_CONTROL}")
        else:
            print(f"[ERROR] 连接失败，错误码: {rc}")

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            cmd = payload.get("command")
            print(f"\n[CTRL] 收到控制指令: {cmd}")

            if cmd == "set_scenario":
                self.apply_scenario(payload["params"]["scenario"])
            elif cmd == "inject_fault":
                self.inject_fault(payload["params"])
            elif cmd == "override_value":
                self.overrides[payload["params"]["target"]] = payload["params"]["value"]
                print(f"[CTRL] 手动微调: {payload['params']['target']} -> {payload['params']['value']}")
            elif cmd == "clear_fault":
                self.clear_fault()

        except Exception as e:
            print(f"[ERROR] 解析控制指令失败: {e}")

    def apply_scenario(self, scenario_name):
        """切换工况目标值 (结合汽车工程实际场景)"""
        self.clear_fault()
        print(f"[SCENARIO] 切换工况 -> {scenario_name}")

        if scenario_name == "static_parking_summer":
            # 夏日静置：车内高温，车外高温，CO2平稳
            self.targets = {"in_car_temp": 65.0, "out_car_temp": 35.0, "humidity": 40.0, "pm25": 30.0, "co2": 400.0}
        elif scenario_name == "winter_cruising":
            # 冬季高速：车内舒适，车外极寒，空调干燥，滤芯净化好
            self.targets = {"in_car_temp": 22.0, "out_car_temp": -10.0, "humidity": 15.0, "pm25": 5.0, "co2": 450.0}
        elif scenario_name == "tunnel_following":
            # 隧道跟车：前车尾气+外循环导致PM2.5和CO2飙升
            self.targets = {"in_car_temp": 24.0, "out_car_temp": 26.0, "humidity": 45.0, "pm25": 180.0, "co2": 2200.0}
        elif scenario_name == "highway_ac_leak":
            # 高速空调漏冷媒：车内温度缓慢上升，湿度异常飙升
            self.targets = {"in_car_temp": 35.0, "out_car_temp": 30.0, "humidity": 85.0, "pm25": 20.0, "co2": 500.0}
        else:
            print(f"[WARN] 未知工况: {scenario_name}")

    def inject_fault(self, params):
        """注入典型传感器故障"""
        self.status = "FAULT"
        target = params.get("target")
        fault_type = params.get("fault_type")

        if fault_type == "STUCK":
            self.fault_code = f"{target.upper()}_STUCK"
            self.overrides[target] = params.get("stuck_value", self.state[target])
            print(f"[FAULT] 注入卡滞故障: {self.fault_code}，卡在 {self.overrides[target]}")
        elif fault_type == "OPEN_CIRCUIT":
            self.fault_code = f"{target.upper()}_OPEN_CIRCUIT"
            self.overrides[target] = 0.0  # 断路通常表现为0
            print(f"[FAULT] 注入断路故障: {self.fault_code}")
        elif fault_type == "SHORT_CIRCUIT":
            self.fault_code = f"{target.upper()}_SHORT"
            # 短路通常表现为最大量程或溢出
            max_vals = {"pm25": 999, "co2": 5000, "in_car_temp": 80, "out_car_temp": 80, "humidity": 100}
            self.overrides[target] = max_vals.get(target, 999.0)
            print(f"[FAULT] 注入短路故障: {self.fault_code}，飙升到 {self.overrides[target]}")

    def clear_fault(self):
        """清除故障与手动覆盖"""
        self.status = "NORMAL"
        self.fault_code = "NONE"
        self.overrides = {}
        print("[INFO] 故障已清除，恢复正常物理仿真")

    def update_physics(self):
        """模拟物理惯性 (一阶低通滤波器算法)"""
        tau = 2.0  # 惯性时间常数 (秒)，越大变化越慢
        dt = 1.0  # 采样周期 (秒)
        alpha = dt / (tau + dt)

        for key in self.state:
            if key not in self.overrides:
                # 加一点高斯白噪声模拟真实传感器抖动
                noise = random.gauss(0, 0.02 * self.targets[key])
                self.state[key] += alpha * (self.targets[key] - self.state[key]) + noise

    def publish_data(self):
        """组装JSON -> 加密 -> 发布"""
        final_data = self.state.copy()
        # 如果有强制覆盖的值（故障或手动微调），使用覆盖值
        final_data.update(self.overrides)

        payload = {
            "timestamp": int(time.time() * 1000),
            "sensor_id": "ENV_SENSOR_001",
            "send_time": time.time() * 1000,  # 保留，用于后端计算网络延迟
            "data": final_data,
            "status": self.status,
            "fault_code": self.fault_code
        }

        # 1. 转为 JSON 字符串
        json_str = json.dumps(payload)

        # 2. AES 加密 (保持你原有系统的安全特色)
        encrypted_payload = encrypt_data(json_str)

        if encrypted_payload:
            # 3. 发送密文
            self.client.publish(TOPIC_DATA, encrypted_payload, qos=1)
            # 打印明文日志方便调试
            print(
                f"[SEND] 密文已发 | 明文状态: {self.status} | 车内温: {final_data['in_car_temp']:.1f}℃ | PM2.5: {final_data['pm25']:.1f}")
        else:
            print("[ERROR] 加密失败")

    def run(self):
        self.client.connect(self.broker_ip, self.port, 60)
        self.client.loop_start()
        print("-" * 50)
        print("车载环境传感器模拟器启动")
        print(f"上行数据主题: {TOPIC_DATA}")
        print("等待工况指令...")
        print("-" * 50)

        try:
            while True:
                self.update_physics()
                self.publish_data()
                time.sleep(1)  # 环境类传感器 1秒采样一次较合理
        except KeyboardInterrupt:
            self.client.loop_stop()
            print("\n[INFO] 模拟器已停止")


if __name__ == "__main__":
    simulator = CarEnvironmentSimulator(broker_ip=BROKER, port=PORT)
    simulator.run()