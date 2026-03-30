# sensor_simulator.py

import paho.mqtt.client as mqtt
import json
import time
import random
import math
from crypto_utils import encrypt_data

# ================= 配置区域 =================
BROKER = "broker.emqx.io"
PORT = 1883
DEVICE_ID = "ESP32_SIM_01"
DATA_TOPIC = f"vehicle/{DEVICE_ID}/sensors/realtime"
CONTROL_TOPIC = f"vehicle/{DEVICE_ID}/sensors/control"  # 新增：用于接收上位机控制指令的主题


# ===========================================


class CarEnvironmentSimulator:
    """
    车载环境传感器模拟器类
    采用面向对象设计，集成一阶惯性物理模型与标准故障注入机制
    """

    def __init__(self, device_id):
        self.device_id = device_id

        # 传感器真实物理状态（带热力学惯性）
        self.state = {
            "temperature": 25.0,  # 车内温度 (℃)
            "humidity": 50.0,  # 车内湿度 (%RH)
            "pm25": 20.0,  # PM2.5 (ug/m³)
            "co2": 450.0  # CO2浓度
        }

        # 目标值（切换工况时修改此值，物理状态会平滑逼近）
        self.targets = self.state.copy()

        # 故障与控制状态
        self.status = "NORMAL"  # 系统状态：NORMAL / FAULT
        self.fault_code = "NONE"  # 故障码
        self.overrides = {}  # 强制覆盖值字典（用于故障注入或手动赋值）

        # 初始化 MQTT 客户端
        self.client = mqtt.Client(client_id=device_id)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """连接回调函数，连接成功后订阅控制主题"""
        if rc == 0:
            print(f"[INFO] 成功连接到 MQTT Broker: {BROKER}")
            # 订阅控制主题，接收上位机的工况切换和故障注入指令
            client.subscribe(CONTROL_TOPIC)
            print(f"[INFO] 已订阅控制主题: {CONTROL_TOPIC}，等待指令...")
        else:
            print(f"[ERROR] 连接失败，错误码: {rc}")

    def _on_message(self, client, userdata, msg):
        """接收并解析上位机的控制指令"""
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
                # 手动微调特定值，用于边界测试
                self.overrides[params.get("target")] = params.get("value")
            elif command == "clear_fault":
                self._clear_fault()
            else:
                print(f"[WARN] 未知指令: {command}")

        except Exception as e:
            print(f"[ERROR] 解析控制指令失败: {e}")

    def _apply_scenario(self, scenario_name):
        """应用预设的车载工况目标值"""
        self._clear_fault()  # 切换工况前自动清除故障

        if scenario_name == "normal_driving":
            self.targets = {"temperature": 24.0, "humidity": 45.0, "pm25": 15.0, "co2": 500.0}
            print("[INFO] 已切换工况：正常行驶")
        elif scenario_name == "summer_traffic_jam":
            # 夏日拥堵：开空调但效果差，尾气严重
            self.targets = {"temperature": 35.0, "humidity": 65.0, "pm25": 120.0, "co2": 1800.0}
            print("[INFO] 已切换工况：夏日拥堵")
        elif scenario_name == "winter_cruising":
            # 冬季高速：车内温暖，外循环导致湿度低，空气质量好
            self.targets = {"temperature": 22.0, "humidity": 20.0, "pm25": 5.0, "co2": 450.0}
            print("[INFO] 已切换工况：冬季巡航")
        else:
            print(f"[WARN] 未知工况: {scenario_name}")

    def _inject_fault(self, params):
        """注入指定的传感器故障"""
        self.status = "FAULT"
        target = params.get("target")
        fault_type = params.get("fault_type")

        if fault_type == "STUCK":
            # 信号卡滞：固定在当前值或指定值
            self.fault_code = f"{target.upper()}_STUCK"
            self.overrides[target] = params.get("stuck_value", self.state.get(target, 0))
        elif fault_type == "OPEN_CIRCUIT":
            # 断路故障：通常表现为跌落至0或极小值
            self.fault_code = f"{target.upper()}_OPEN_CIRCUIT"
            self.overrides[target] = 0.0
        elif fault_type == "SHORT_CIRCUIT":
            # 短路故障：通常表现为超出量程的最大值
            self.fault_code = f"{target.upper()}_SHORT_CIRCUIT"
            max_vals = {"temperature": 150.0, "humidity": 100.0, "pm25": 999.0, "co2": 5000.0}
            self.overrides[target] = max_vals.get(target, 999.0)

        print(f"[INFO] 已注入故障: {self.fault_code}")

    def _clear_fault(self):
        """清除所有故障与手动覆盖，恢复正常物理仿真"""
        self.status = "NORMAL"
        self.fault_code = "NONE"
        self.overrides.clear()
        print("[INFO] 已清除故障，恢复正常物理仿真")

    def _update_physics(self):
        """
        核心物理引擎：一阶低通滤波器模拟热力学/空气动力学惯性
        替代原先的简单正弦波和随机跳变，使曲线更加符合真实车规
        """
        tau = 5.0  # 惯性时间常数(秒)，值越大越迟钝
        dt = 2.0  # 采样周期(秒)，需与主循环sleep时间一致
        alpha = dt / (tau + dt)

        for key in self.state:
            if key not in self.overrides:
                # 计算目标逼近 + 高斯白噪声(模拟ADC采集抖动)
                noise = random.gauss(0, 0.1)
                self.state[key] += alpha * (self.targets[key] - self.state[key]) + noise
                # 物理量限幅保护
                self.state[key] = round(self.state[key], 2)

    def get_payload_dict(self):
        """
        生成符合原系统格式的数据字典
        保留了原有的 device_id, timestamp, send_time 结构
        在 status 中新增了 sensor_state 和 fault_code 供上位机解析
        """
        # 深拷贝当前物理状态
        final_data = self.state.copy()
        # 如果有故障注入或强制覆盖，使用覆盖值替换真实物理值
        final_data.update(self.overrides)

        # 针对温度和湿度进行四舍五入，保持与原代码一致的数据精度
        final_data["temperature"] = round(final_data.get("temperature", 0), 2)
        final_data["humidity"] = round(final_data.get("humidity", 0), 2)

        payload_dict = {
            "device_id": self.device_id,
            "timestamp": int(time.time()),
            "send_time": time.time() * 1000,
            "data": final_data,
            "status": {
                "wifi_rssi": random.randint(-60, -40),
                "sensor_state": self.status,  # 新增字段：当前传感器健康状态
                "fault_code": self.fault_code  # 新增字段：具体故障码
            }
        }
        return payload_dict

    def run(self):
        """启动模拟器主循环"""
        try:
            print(f"[INFO] 正在连接 {BROKER}...")
            self.client.connect(BROKER, PORT, 60)
            self.client.loop_start()
            print(f"[INFO] 开始发送【加密】数据到 Topic: {DATA_TOPIC}")
            print("-" * 50)

            while True:
                # 1. 物理引擎更新（模拟时间流逝带来的状态变化）
                self._update_physics()

                # 2. 获取组装好的数据字典
                payload_dict = self.get_payload_dict()

                # 3. 转为 JSON 字符串
                json_str = json.dumps(payload_dict)

                # 4. 加密处理
                encrypted_payload = encrypt_data(json_str)

                if encrypted_payload:
                    # 5. 通过MQTT发送密文
                    self.client.publish(DATA_TOPIC, encrypted_payload, qos=1)

                    # 打印日志（展示原始明文关键数据，方便调试）
                    temp = payload_dict['data']['temperature']
                    hum = payload_dict['data']['humidity']
                    state_info = payload_dict['status']['sensor_state']
                    print(f"[INFO] Sent: 状态[{state_info}] | 原始温度: {temp}℃, 原始湿度: {hum}%")
                else:
                    print("[ERROR] 加密失败，跳过本次发送")

                # 2秒采样周期
                time.sleep(2)

        except KeyboardInterrupt:
            self.client.loop_stop()
            print("\n[INFO] 模拟器已停止")
        except Exception as e:
            print(f"[ERROR] 发生严重错误: {e}")


if __name__ == "__main__":
    # 实例化并运行模拟器
    simulator = CarEnvironmentSimulator(DEVICE_ID)
    simulator.run()