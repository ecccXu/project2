# backend/test_bench.py

import time
import json
import logging
import threading
from datetime import datetime
import operator # 新增：用于动态执行比较运算
import os
import uuid # 用于生成唯一用例 ID

import main as backend_main
from crypto_utils import decrypt_data

logger = logging.getLogger("TestBenchExecutor")


class TestBenchExecutor:
    def __init__(self):
        self.is_running = False
        self.current_case_name = "无"
        self.progress = 0
        self.total_cases = 0  # 动态计算，不再写死为4

        self.results = []
        self.logs = []
        self._thread = None

        # 定义自定义用例的持久化文件路径
        self.custom_cases_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "custom_cases.json")
        # 初始化用例注册中心
        self.registry = self._build_registry()

    # ==========================================
    # 核心动作方法
    # ==========================================
    def _log(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_str = f"[{timestamp}] {msg}"
        logger.info(log_str)
        self.logs.append(log_str)

    def _send_command(self, command, params):
        if not backend_main.mqtt_client_instance:
            self._log("错误：MQTT 客户端未就绪！")
            return False
        payload = json.dumps({"command": command, "params": params})
        topic = "vcar/sensors/environment/control"
        backend_main.mqtt_client_instance.publish(topic, payload, qos=1)
        self._log(f"-> 下发指令: {command} | 参数: {params}")
        return True

    def _wait(self, seconds):
        for i in range(int(seconds * 10)):
            time.sleep(0.1)

    def _get_latest(self):
        with backend_main.data_lock:
            return backend_main.latest_sensor_data.copy()

    def _get_queue_tail(self, count=10):
        with backend_main.data_lock:
            queue_list = list(backend_main.data_queue)
            return queue_list[-count:] if len(queue_list) >= count else queue_list

    def _build_registry(self):
        # 1. 基础预置用例
        base_registry = {
            "case_temp_step": {
                "name": "极限温度阶跃响应测试",
                "type": "dynamic_performance",
                "default_params": {"base_temp": 20.0, "target_temp": 80.0, "timeout": 15.0, "max_overshoot": 2.0},
                "executor": self._case_1_temp_step_response
            },
            "case_fault_diagnosis": {
                "name": "硬件断路故障诊断测试",
                "type": "fault_injection",
                "default_params": {"target": "in_car_temp", "fault_type": "OPEN_CIRCUIT", "capture_timeout": 5.0},
                "executor": self._case_2_hardware_fault_diagnosis
            },
            "case_scenario_anti": {
                "name": "复杂工况动态抗扰测试",
                "type": "scenario_follow",
                "default_params": {"scenario_name": "tunnel_following", "wait_time": 15.0, "check_samples": 10},
                "executor": self._case_3_complex_scenario_anti_interference
            },
            "case_aes_tamper": {
                "name": "安全通信链路抗篡改测试",
                "type": "security",
                "default_params": {},
                "executor": self._case_4_aes_tamper_resistance
            }
        }

        # 2. 动态加载自定义用例文件
        custom_cases = self._load_custom_cases_from_file()
        for case in custom_cases:
            base_registry[case["id"]] = {
                "name": case["name"],
                "type": "custom",
                # 注意：自定义用例的 default_params 就是它自己本身（包含 name 和 steps）
                "default_params": case,
                "executor": self._execute_custom_steps
            }

        return base_registry

    def _load_custom_cases_from_file(self):
        """从 JSON 文件读取自定义用例"""
        if not os.path.exists(self.custom_cases_file):
            return []
        try:
            with open(self.custom_cases_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取自定义用例文件失败: {e}")
            return []

    def reload_registry(self):
        """提供对外接口，当文件变更时重新加载注册表"""
        self.registry = self._build_registry()

    # ==========================================
    # 测试用例实现（改造为接收 params 字典）
    # ==========================================

    def _case_1_temp_step_response(self, params):
        """用例1：从 params 中读取温度阈值，动态执行阶跃测试"""
        case_name = f"阶跃响应测试 (目标: {params['target_temp']}℃)"
        self.current_case_name = case_name
        self._log(f"========== 开始执行: {case_name} ==========")
        start_time = time.time()
        result = {"case": case_name, "status": "PASS", "details": []}

        try:
            # 1. 建立基准（读取参数）
            self._send_command("override_value", {"target": "in_car_temp", "value": params["base_temp"]})
            self._wait(8)

            # 2. 阶跃动作
            self._send_command("override_value", {"target": "in_car_temp", "value": params["target_temp"]})
            self._log(f"已下发阶跃指令 -> {params['target_temp']}℃")

            # 3. 捕获响应
            max_temp_seen = self._get_latest()["in_car_temp"]
            time_out = False
            reached_target = False
            start_measure = time.time()
            target_90 = params["target_temp"] * 0.9  # 到达90%算响应

            while time.time() - start_measure < params["timeout"]:
                data = self._get_latest()
                temp = data["in_car_temp"]
                max_temp_seen = max(max_temp_seen, temp)

                if temp >= target_90 and not reached_target:
                    response_time = time.time() - start_measure
                    self._log(f"到达目标区域 {target_90}℃ (耗时: {response_time:.2f}s)")
                    reached_target = True
                    break
                time.sleep(0.1)
            else:
                time_out = True

            # 4. 动态断言（读取参数）
            if time_out:
                result["status"] = "FAIL"
                result["details"].append(f"响应超时：未在{params['timeout']}s内达到目标")

            overshoot = max_temp_seen - params["target_temp"]
            if overshoot > params["max_overshoot"]:
                result["status"] = "FAIL"
                result["details"].append(f"超调量过大：峰值 {max_temp_seen:.1f}℃ (超调 {overshoot:.1f}℃)")
            else:
                result["details"].append(f"动态响应良好 (超调: {overshoot:.1f}℃)")

        except Exception as e:
            result["status"] = "ERROR"
            result["details"].append(f"用例执行异常: {str(e)}")
        finally:
            self._send_command("clear_fault", {})
            result["duration"] = round(time.time() - start_time, 2)
            self.results.append(result)
            self._log(f"========== 结束执行: {case_name} [{result['status']}] ==========")

    def _case_2_hardware_fault_diagnosis(self, params):
        """用例2：根据 params 动态注入指定故障"""
        case_name = f"故障诊断测试 (目标: {params['target']} - {params['fault_type']})"
        self.current_case_name = case_name
        self._log(f"========== 开始执行: {case_name} ==========")
        start_time = time.time()
        result = {"case": case_name, "status": "PASS", "details": []}

        try:
            self._send_command("clear_fault", {})
            self._wait(2)

            self._send_command("inject_fault", {"target": params["target"], "fault_type": params["fault_type"]})

            fault_captured = False
            start_capture = time.time()
            captured_fault_code = ""
            expected_code = f"{params['target'].upper()}_{params['fault_type']}"

            while time.time() - start_capture < params["capture_timeout"]:
                data = self._get_latest()
                if data["status"] == "FAULT":
                    fault_captured = True
                    captured_fault_code = data["fault_code"]
                    self._log(f"成功捕获故障上报: {captured_fault_code}")
                    break
                time.sleep(0.1)

            if not fault_captured:
                result["status"] = "FAIL"
                result["details"].append(f"诊断失效：{params['capture_timeout']}s内未接收到故障状态")
            elif captured_fault_code != expected_code:
                result["status"] = "FAIL"
                result["details"].append(f"诊断错误：预期 {expected_code}，实际 {captured_fault_code}")
            else:
                result["details"].append(f"FDI 逻辑准确，故障识别及时")
        except Exception as e:
            result["status"] = "ERROR"
            result["details"].append(f"用例执行异常: {str(e)}")
        finally:
            self._send_command("clear_fault", {})
            result["duration"] = round(time.time() - start_time, 2)
            self.results.append(result)
            self._log(f"========== 结束执行: {case_name} [{result['status']}] ==========")

    def _case_3_complex_scenario_anti_interference(self, params):
        """用例3：动态切换工况并校验"""
        case_name = f"抗扰测试 (工况: {params['scenario_name']})"
        self.current_case_name = case_name
        self._log(f"========== 开始执行: {case_name} ==========")
        start_time = time.time()
        result = {"case": case_name, "status": "PASS", "details": []}

        try:
            self._send_command("set_scenario", {"scenario": params["scenario_name"]})
            self._wait(params["wait_time"])

            tail_data = self._get_queue_tail(params["check_samples"])
            if len(tail_data) < 5:
                result["status"] = "FAIL"
                result["details"].append("数据采集不足")
            else:
                # 简单校验：PM2.5 或 CO2 应该有所变化，这里以 PM2.5 大于 100 为例粗略判定
                avg_pm25 = sum(d["pm25"] for d in tail_data) / len(tail_data)
                self._log(f"工况稳态分析: 平均PM2.5={avg_pm25:.1f}")
                if avg_pm25 < 50:  # 如果切换了污染工况，PM不应该还这么低
                    result["status"] = "FAIL"
                    result["details"].append(f"抗扰异常：工况未生效，PM2.5均值仅 {avg_pm25:.1f}")
                else:
                    result["details"].append(f"工况跟随正常 (均值PM2.5: {avg_pm25:.1f})")
        except Exception as e:
            result["status"] = "ERROR"
            result["details"].append(f"用例执行异常: {str(e)}")
        finally:
            self._send_command("clear_fault", {})
            result["duration"] = round(time.time() - start_time, 2)
            self.results.append(result)
            self._log(f"========== 结束执行: {case_name} [{result['status']}] ==========")

    def _case_4_aes_tamper_resistance(self, params):
        """用例4：安全测试，无需参数"""
        case_name = "安全通信链路抗篡改测试"
        self.current_case_name = case_name
        self._log(f"========== 开始执行: {case_name} ==========")
        start_time = time.time()
        result = {"case": case_name, "status": "PASS", "details": []}

        try:
            fake_payload = "dGVzdF9hbHRlcmVkX3N0cmluZw=="
            self._log("注入被篡改的数据包...")
            decrypt_result = decrypt_data(fake_payload)

            if decrypt_result is not None:
                result["status"] = "FAIL"
                result["details"].append("安全防线崩溃：成功解密了被篡改的数据！")
            else:
                result["details"].append("安全防线有效：成功拦截篡改数据")
        except Exception as e:
            if "Padding" in str(e) or "CRC" in str(e):
                result["details"].append(f"底层抛出预期异常 ({type(e).__name__})，系统具备抗篡改韧性")
            else:
                result["status"] = "ERROR"
                result["details"].append(f"发生非预期异常: {str(e)}")

        result["duration"] = round(time.time() - start_time, 2)
        self.results.append(result)
        self._log(f"========== 结束执行: {case_name} [{result['status']}] ==========")

    # ==========================================
    # 通用 DSL 解释器引擎
    # ==========================================
    def _execute_custom_steps(self, params):
        """
        解释并执行用户在前端编排的 JSON 步骤列表
        :param params: 字典，必须包含 "steps" 键
        """
        # 获取步骤列表，如果没有则直接报错
        steps = params.get("steps", [])
        if not steps:
            raise ValueError("自定义用例缺少 steps 步骤定义")

        # 定义运算符映射表，将 JSON 字符串映射为 Python 的 operator 函数
        ops_map = {
            ">": operator.gt,
            "<": operator.lt,
            "==": operator.eq,
            "!=": operator.ne,
            ">=": operator.ge,
            "<=": operator.le
        }

        case_name = params.get("name", "未命名自定义用例")
        self.current_case_name = case_name
        self._log(f"========== 开始执行自定义用例: {case_name} ==========")
        self._log(f"共加载 {len(steps)} 个步骤积木")
        start_time = time.time()
        result = {"case": case_name, "status": "PASS", "details": []}

        try:
            for index, step in enumerate(steps, start=1):
                step_type = step.get("type")
                action_name = step.get("action")
                step_params = step.get("params", {})

                self._log(f"[步骤 {index}] 解析积木: {step_type} -> {action_name}")

                # ----------------- 处理动作积木 -----------------
                if step_type == "action":
                    if action_name == "WAIT":
                        self._wait(step_params.get("seconds", 1))
                    elif action_name in ["SET_SCENARIO", "INJECT_FAULT", "OVERRIDE_VALUE", "CLEAR_FAULT"]:
                        self._send_command(action_name.lower(), step_params)
                    else:
                        self._log(f"警告：未知的动作指令 '{action_name}'，跳过")

                # ----------------- 处理断言积木 -----------------
                elif step_type == "assertion":
                    # 每次断言前稍微等一下，给底层数据流动一点时间
                    self._wait(0.5)
                    latest_data = self._get_latest()

                    if action_name == "ASSERT_VALUE":
                        target_key = step_params.get("target")
                        op_symbol = step_params.get("operator")
                        expected = step_params.get("expected_value")

                        actual_val = latest_data.get(target_key, 0)
                        op_func = ops_map.get(op_symbol)

                        if not op_func:
                            raise ValueError(f"断言错误：不支持的运算符 '{op_symbol}'")

                        # 动态执行比较：例如 operator.gt(actual_val, expected)
                        is_pass = op_func(float(actual_val), float(expected))

                        if is_pass:
                            self._log(f"  ✅ 断言通过: {target_key} ({actual_val}) {op_symbol} {expected}")
                        else:
                            raise AssertionError(
                                f"断言失败: {target_key} 实际值 {actual_val}, 期望 {op_symbol} {expected}")

                    elif action_name == "ASSERT_STATUS":
                        expected_status = step_params.get("expected_status")
                        actual_status = latest_data.get("status")
                        if actual_status == expected_status:
                            self._log(f"  ✅ 断言通过: 状态码匹配 [{actual_status}]")
                        else:
                            raise AssertionError(f"断言失败: 期望状态 [{expected_status}], 实际 [{actual_status}]")

                    elif action_name == "ASSERT_FAULT_CODE":
                        expected_code = step_params.get("expected_code")
                        actual_code = latest_data.get("fault_code")
                        if actual_code == expected_code:
                            self._log(f"  ✅ 断言通过: 故障码匹配 [{actual_code}]")
                        else:
                            raise AssertionError(f"断言失败: 期望故障码 [{expected_code}], 实际 [{actual_code}]")
                    else:
                        self._log(f"警告：未知的断言指令 '{action_name}'")

                time.sleep(0.5)  # 步骤间短暂停顿

        except AssertionError as e:
            # 捕获断言失败，标记用例 FAIL，并跳出循环
            result["status"] = "FAIL"
            result["details"].append(str(e))
            self._log(f"❌ 流程中断：{str(e)}")
        except Exception as e:
            result["status"] = "ERROR"
            result["details"].append(f"执行期发生异常: {str(e)}")
            self._log(f"❌ 流程崩溃：{str(e)}")
        finally:
            # 确保测试结束后清理现场
            self._send_command("clear_fault", {})
            result["duration"] = round(time.time() - start_time, 2)
            self.results.append(result)
            self._log(f"========== 结束执行: {case_name} [{result['status']}] ==========")

    # ==========================================
    # 调度引擎（核心重构：支持动态配置解析）
    # ==========================================
    def _run_suite(self, selected_cases_config):
        """
        根据传入的配置列表动态执行用例
        :param selected_cases_config: 列表，例如:
            [
                {"id": "case_temp_step", "params": {"target_temp": 85.0}},
                {"id": "case_aes_tamper", "params": {}}
            ]
        """
        self.is_running = True
        self.results = []
        self.logs = []
        self.total_cases = len(selected_cases_config)
        self.progress = 0

        self._log("==================================================")
        self._log(f"   台架测试启动 | 本次执行 {self.total_cases} 个用例")
        self._log("==================================================")

        for case_config in selected_cases_config:
            case_id = case_config.get("id")
            custom_params = case_config.get("params", {})

            # 1. 从注册中心查找用例元数据
            case_meta = self.registry.get(case_id)

            if not case_meta:
                self._log(f"警告：找不到用例 ID '{case_id}'，跳过执行！")
                self.progress += 1
                continue

            # 2. 合并参数：用自定义参数覆盖默认参数 (实现参数编辑功能的后端支撑)
            final_params = case_meta["default_params"].copy()
            final_params.update(custom_params)

            # 3. 动态获取并执行绑定的测试函数
            executor_func = case_meta["executor"]
            try:
                # 将合并后的参数字典传入执行器
                executor_func(final_params)
            except Exception as e:
                self._log(f"致命错误：执行 {case_id} 时发生未捕获异常: {str(e)}")

            self.progress += 1
            self._wait(2)  # 用例间隔，让系统恢复平静

        self.is_running = False
        self.current_case_name = "测试完成"
        self._log("==================================================")
        self._log("   选中用例执行完毕！")
        self._log("==================================================")

    def start(self, config=[]):
        """外部调用接口：开启测试线程，传入配置列表"""
        if self.is_running:
            return False
        if not config:
            self._log("错误：未接收到任何测试用例配置！")
            return False

        self._thread = threading.Thread(target=self._run_suite, args=(config,), daemon=True)
        self._thread.start()
        return True


# 实例化全局执行器
executor = TestBenchExecutor()