# sensor_simulator.py

import paho.mqtt.client as mqtt
import json
import time
import random
from crypto_utils import encrypt_data
import os

# ================= 配置区域 =================
BROKER = os.environ.get('MQTT_BROKER', 'localhost')
PORT = int(os.environ.get('MQTT_PORT', '1883'))
SENSOR_ID = "ENV_SIM_001"
DATA_TOPIC = f"vcar/sensors/{SENSOR_ID}/data"
CONTROL_TOPIC = f"vcar/sensors/{SENSOR_ID}/control"


# ===========================================


class CarEnvironmentSimulator:
    def __init__(self, sensor_id):
        self.sensor_id = sensor_id

        self.state = {
            "in_car_temp": 25.0,
            "out_car_temp": 25.0,
            "humidity": 50.0,
            "pm25": 20.0,
            "co2": 400.0
        }

        self.targets = self.state.copy()

        self.status = "NORMAL"
        self.fault_code = "NONE"
        self.overrides = {}

        self.client = mqtt.Client(client_id=sensor_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        if rc == 0:
            print(f"[INFO] 成功连接到 MQTT Broker: {BROKER}")
            client.subscribe(CONTROL_TOPIC)
            print(f"[INFO] 已订阅控制主题: {CONTROL_TOPIC}，等待指令...")
        else:
            print(f"[ERROR] 连接失败，错误码: {rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            command = payload.get("command")
            params = payload.get("params", {})
            print(f"[INFO] 收到控制指令 -> {command}")

            if command == "set_scenario":
                self._apply_scenario(params.get("scenario"))
            elif command == "inject_fault":
                self._inject_fault(params)
            elif command == "override_value":
                self.overrides[params.get("target")] = params.get("value")
            elif command == "clear_fault":
                self._clear_fault()
        except Exception as e:
            print(f"[ERROR] 解析控制指令失败: {e}")

    def _apply_scenario(self, scenario_name):
        self._clear_fault()
        if scenario_name == "static_parking_summer":
            self.targets = {"in_car_temp": 65.0, "out_car_temp": 35.0, "humidity": 40.0, "pm25": 30.0, "co2": 400.0}
            print("[INFO] 已切换工况：夏日静置 (车内高温)")
        elif scenario_name == "winter_cruising":
            self.targets = {"in_car_temp": 22.0, "out_car_temp": -10.0, "humidity": 15.0, "pm25": 5.0, "co2": 450.0}
            print("[INFO] 已切换工况：冬季高速巡航")
        elif scenario_name == "tunnel_following":
            self.targets = {"in_car_temp": 24.0, "out_car_temp": 26.0, "humidity": 45.0, "pm25": 180.0, "co2": 2200.0}
            print("[INFO] 已切换工况：隧道跟车 (尾气污染)")
        elif scenario_name == "highway_ac_leak":
            self.targets = {"in_car_temp": 35.0, "out_car_temp": 30.0, "humidity": 85.0, "pm25": 20.0, "co2": 500.0}
            print("[INFO] 已切换工况：高速空调漏气")
        else:
            print(f"[WARN] 未知工况: {scenario_name}")

    def _inject_fault(self, params):
        self.status = "FAULT"
        target = params.get("target")
        fault_type = params.get("fault_type")

        if fault_type == "STUCK":
            self.fault_code = f"{target.upper()}_STUCK"
            self.overrides[target] = params.get("stuck_value", self.state.get(target, 0))
        elif fault_type == "OPEN_CIRCUIT":
            self.fault_code = f"{target.upper()}_OPEN_CIRCUIT"
            self.overrides[target] = 0.0
        elif fault_type == "SHORT_CIRCUIT":
            self.fault_code = f"{target.upper()}_SHORT_CIRCUIT"
            max_vals = {"pm25": 999, "co2": 5000, "in_car_temp": 80, "out_car_temp": 80, "humidity": 100}
            self.overrides[target] = max_vals.get(target, 999.0)
        print(f"[INFO] 已注入故障: {self.fault_code}")

    def _clear_fault(self):
        self.status = "NORMAL"
        self.fault_code = "NONE"
        self.overrides.clear()
        print("[INFO] 已清除故障，恢复正常物理仿真")

    def _update_physics(self):
        tau = 5.0
        dt = 2.0
        alpha = dt / (tau + dt)
        for key in self.state:
            if key not in self.overrides:
                noise = random.gauss(0, 0.1)
                self.state[key] += alpha * (self.targets[key] - self.state[key]) + noise
                self.state[key] = round(self.state[key], 2)

    def _get_payload_dict(self):
        final_data = self.state.copy()
        final_data.update(self.overrides)

        payload_dict = {
            "timestamp": int(time.time() * 1000),
            "sensor_id": self.sensor_id,
            "send_time": time.time() * 1000,
            "data": final_data,
            "status": self.status,
            "fault_code": self.fault_code
        }
        return payload_dict

    def run(self):
        try:
            print(f"[INFO] 正在连接 {BROKER}...")
            self.client.connect(BROKER, PORT, 60)
            self.client.loop_start()
            print(f"[INFO] 开始发送【加密】数据到 Topic: {DATA_TOPIC}")
            print("-" * 50)

            while True:
                self._update_physics()
                payload_dict = self._get_payload_dict()
                json_str = json.dumps(payload_dict)
                encrypted_payload = encrypt_data(json_str)

                if encrypted_payload:
                    self.client.publish(DATA_TOPIC, encrypted_payload, qos=1)
                    temp = payload_dict['data']['in_car_temp']
                    pm = payload_dict['data']['pm25']
                    state_info = payload_dict['status']
                    print(f"[SEND] 状态[{state_info}] | 车内温: {temp}℃ | PM2.5: {pm}")
                else:
                    print("[ERROR] 加密失败，跳过本次发送")

                time.sleep(2)

        except KeyboardInterrupt:
            self.client.loop_stop()
            print("\n[INFO] 模拟器已停止")
        except Exception as e:
            print(f"[ERROR] 发生严重错误: {e}")

if __name__ == "__main__":
    simulator = CarEnvironmentSimulator(SENSOR_ID)
    simulator.run()