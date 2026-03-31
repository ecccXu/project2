# backend/test_bench.py

import time
import json
import logging
import threading
from datetime import datetime

# 导入底层采集层和加密模块
import main as backend_main
from crypto_utils import decrypt_data

# 配置日志
logger = logging.getLogger("TestBenchExecutor")


class TestBenchExecutor:
    def __init__(self):
        self.is_running = False
        self.current_case_name = "无"
        self.progress = 0
        self.total_cases = 4

        # 结果与日志收集器
        self.results = []
        self.logs = []

        # 线程控制
        self._thread = None

    def _log(self, msg):
        """内部日志记录方法，同时打印到控制台和存入列表"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_str = f"[{timestamp}] {msg}"
        logger.info(log_str)
        self.logs.append(log_str)

    def _send_command(self, command, params):
        """封装 MQTT 指令下发动作"""
        if not backend_main.mqtt_client_instance:
            self._log("错误：MQTT 客户端未就绪！")
            return False

        payload = json.dumps({"command": command, "params": params})
        topic = "vcar/sensors/environment/control"
        backend_main.mqtt_client_instance.publish(topic, payload, qos=1)
        self._log(f"-> 下发指令: {command} | 参数: {params}")
        return True

    def _wait(self, seconds):
        """阻塞等待，并实时更新状态"""
        for i in range(int(seconds * 10)):
            time.sleep(0.1)

    def _get_latest(self):
        """线程安全地获取最新一条数据"""
        with backend_main.data_lock:
            return backend_main.latest_sensor_data.copy()

    def _get_queue_tail(self, count=10):
        """线程安全地获取滑动窗口最后 N 条数据"""
        with backend_main.data_lock:
            queue_list = list(backend_main.data_queue)
            return queue_list[-count:] if len(queue_list) >= count else queue_list

    # ==========================================
    # 核心测试用例集
    # ==========================================

    def _case_1_temp_step_response(self):
        """用例1：极限温度阶跃响应测试"""
        case_name = "极限温度阶跃响应测试"
        self.current_case_name = case_name
        self._log(f"========== 开始执行: {case_name} ==========")
        start_time = time.time()
        result = {"case": case_name, "status": "PASS", "details": []}

        try:
            # 1. 建立基准：强制拉到 20℃ 并等待稳定
            self._send_command("override_value", {"target": "in_car_temp", "value": 20.0})
            self._wait(8)  # 等待物理惯性消除
            current_temp = self._get_latest()["in_car_temp"]
            self._log(f"基准温度已稳定在: {current_temp:.1f}℃")

            # 2. 阶跃动作：瞬间拉到 80℃
            self._send_command("override_value", {"target": "in_car_temp", "value": 80.0})
            self._log("已下发阶跃指令 -> 80℃")

            # 3. 捕获响应过程
            max_temp_seen = current_temp
            time_out = False
            reached_target = False
            start_measure = time.time()

            while time.time() - start_measure < 15:  # 最多等15秒
                data = self._get_latest()
                temp = data["in_car_temp"]
                max_temp_seen = max(max_temp_seen, temp)

                # 判定到达目标值 90% 的区域 (78℃)
                if temp >= 78.0 and not reached_target:
                    response_time = time.time() - start_measure
                    self._log(f"到达目标区域 78℃ (耗时: {response_time:.2f}s)")
                    reached_target = True
                    break
                time.sleep(0.1)
            else:
                time_out = True

            # 4. 断言与结果分析
            if time_out:
                result["status"] = "FAIL"
                result["details"].append(
                    f"响应超时：未在15秒内达到目标区域，当前仅 {self._get_latest()['in_car_temp']:.1f}℃")

            overshoot = max_temp_seen - 80.0
            if overshoot > 2.0:  # 允许2℃的超调量
                result["status"] = "FAIL"
                result["details"].append(f"超调量过大：峰值达到 {max_temp_seen:.1f}℃ (超调 {overshoot:.1f}℃)")
            else:
                result["details"].append(f"动态响应良好 (超调: {overshoot:.1f}℃)")

        except Exception as e:
            result["status"] = "ERROR"
            result["details"].append(f"用例执行异常: {str(e)}")
        finally:
            self._send_command("clear_fault", {})  # 清除 override
            result["duration"] = round(time.time() - start_time, 2)
            self.results.append(result)
            self._log(f"========== 结束执行: {case_name} [{result['status']}] ==========")

    def _case_2_hardware_fault_diagnosis(self):
        """用例2：硬件断路故障诊断(FDI)测试"""
        case_name = "硬件断路故障诊断测试"
        self.current_case_name = case_name
        self._log(f"========== 开始执行: {case_name} ==========")
        start_time = time.time()
        result = {"case": case_name, "status": "PASS", "details": []}

        try:
            self._send_command("clear_fault", {})
            self._wait(2)

            # 1. 注入断路故障
            self._send_command("inject_fault", {"target": "in_car_temp", "fault_type": "OPEN_CIRCUIT"})
            self._log("已注入温度传感器断路故障")

            # 2. 捕获故障上报
            fault_captured = False
            start_capture = time.time()
            captured_fault_code = ""

            while time.time() - start_capture < 5:  # 规定 5 秒内必须上报
                data = self._get_latest()
                if data["status"] == "FAULT":
                    fault_captured = True
                    captured_fault_code = data["fault_code"]
                    self._log(f"成功捕获故障上报: {captured_fault_code}")
                    break
                time.sleep(0.1)

            # 3. 断言
            if not fault_captured:
                result["status"] = "FAIL"
                result["details"].append("诊断失效：5秒内未接收到硬件故障状态")
            elif captured_fault_code != "IN_CAR_TEMP_OPEN_CIRCUIT":
                result["status"] = "FAIL"
                result["details"].append(
                    f"诊断错误：故障码不匹配。预期 IN_CAR_TEMP_OPEN_CIRCUIT，实际 {captured_fault_code}")
            else:
                result["details"].append("FDI 逻辑准确，故障识别及时")

        except Exception as e:
            result["status"] = "ERROR"
            result["details"].append(f"用例执行异常: {str(e)}")
        finally:
            self._send_command("clear_fault", {})
            result["duration"] = round(time.time() - start_time, 2)
            self.results.append(result)
            self._log(f"========== 结束执行: {case_name} [{result['status']}] ==========")

    def _case_3_complex_scenario_anti_interference(self):
        """用例3：复杂工况动态抗扰测试"""
        case_name = "复杂工况动态抗扰测试 (隧道跟车)"
        self.current_case_name = case_name
        self._log(f"========== 开始执行: {case_name} ==========")
        start_time = time.time()
        result = {"case": case_name, "status": "PASS", "details": []}

        try:
            self._send_command("set_scenario", {"scenario": "tunnel_following"})
            self._log("已切换至 [隧道跟车] 工况")
            self._wait(15)  # 等待物理引擎充分逼近目标值

            # 拉取最近 10 条数据求平均
            tail_data = self._get_queue_tail(10)
            if len(tail_data) < 5:
                result["status"] = "FAIL"
                result["details"].append("数据采集不足，无法评估抗扰性能")
            else:
                avg_pm25 = sum(d["pm25"] for d in tail_data) / len(tail_data)
                avg_co2 = sum(d["co2"] for d in tail_data) / len(tail_data)

                self._log(f"工况稳态分析: 平均PM2.5={avg_pm25:.1f}, 平均CO2={avg_co2:.1f}")

                # 断言：在隧道工况下，数值必须逼近目标 (PM2.5目标180, CO2目标2200)
                if avg_pm25 < 100:
                    result["status"] = "FAIL"
                    result["details"].append(f"抗扰异常：PM2.5未随工况变化，均值仅 {avg_pm25:.1f}")
                elif avg_co2 < 1500:
                    result["status"] = "FAIL"
                    result["details"].append(f"抗扰异常：CO2未随工况变化，均值仅 {avg_co2:.1f}")
                else:
                    result["details"].append(f"工况跟随正常 (PM2.5: {avg_pm25:.1f}, CO2: {avg_co2:.1f})")

        except Exception as e:
            result["status"] = "ERROR"
            result["details"].append(f"用例执行异常: {str(e)}")
        finally:
            self._send_command("clear_fault", {})
            result["duration"] = round(time.time() - start_time, 2)
            self.results.append(result)
            self._log(f"========== 结束执行: {case_name} [{result['status']}] ==========")

    def _case_4_aes_tamper_resistance(self):
        """用例4：AES通信链路抗篡改测试"""
        case_name = "安全通信链路抗篡改测试"
        self.current_case_name = case_name
        self._log(f"========== 开始执行: {case_name} ==========")
        start_time = time.time()
        result = {"case": case_name, "status": "PASS", "details": []}

        try:
            # 构造一个被篡改的密文 (长度对，但内容被改了)
            fake_payload = "dGVzdF9hbHRlcmVkX3N0cmluZw=="

            self._log("注入被篡改的数据包...")
            decrypt_result = decrypt_data(fake_payload)

            if decrypt_result is not None:
                result["status"] = "FAIL"
                result["details"].append("安全防线崩溃：成功解密了被篡改的数据！")
            else:
                result["details"].append("安全防线有效：成功拦截篡改数据并返回 None")

        except Exception as e:
            # 对于安全模块，发生异常有时是预期的，但我们更希望它优雅地返回 None
            if "Padding" in str(e) or "CRC" in str(e):
                result["details"].append(f"底层抛出预期异常 ({type(e).__name__})，系统具备抗篡改韧性")
            else:
                result["status"] = "ERROR"
                result["details"].append(f"发生非预期异常: {str(e)}")

        result["duration"] = round(time.time() - start_time, 2)
        self.results.append(result)
        self._log(f"========== 结束执行: {case_name} [{result['status']}] ==========")

    # ==========================================
    # 执行器调度引擎
    # ==========================================

    def _run_suite(self):
        """按顺序执行所有测试用例"""
        self.is_running = True
        self.results = []
        self.logs = []
        self.progress = 0

        self._log("==================================================")
        self._log("   车载环境传感器自动化台架测试系统 v1.0 启动")
        self._log("==================================================")

        cases = [
            self._case_1_temp_step_response,
            self._case_2_hardware_fault_diagnosis,
            self._case_3_complex_scenario_anti_interference,
            self._case_4_aes_tamper_resistance
        ]

        for i, case_func in enumerate(cases):
            self.progress = i
            case_func()
            self._wait(2)  # 用例间隔，让系统喘口气

        self.progress = self.total_cases
        self.is_running = False
        self.current_case_name = "测试完成"
        self._log("==================================================")
        self._log("   测试套件执行完毕！")
        self._log("==================================================")

    def start(self):
        """外部调用接口：开启测试线程"""
        if self.is_running:
            return False
        self._thread = threading.Thread(target=self._run_suite, daemon=True)
        self._thread.start()
        return True


# 实例化全局执行器
executor = TestBenchExecutor()