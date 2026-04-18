# backend/test_bench.py

import time
import logging
import threading
from collections import deque
from datetime import datetime
from typing import Callable, Optional

from crypto_utils import decrypt_data

logger = logging.getLogger("TestBenchExecutor")


class TestBenchExecutor:
    """
    台架自动化测试执行器（第二层测试能力）

    职责：
      主动向传感器节点下发指令，观察其响应，
      验证传感器的动态性能、故障诊断能力和安全性

    与 test_engine.py 的区别：
      test_engine：被动式，数据进来就校验阈值
      test_bench ：主动式，下发指令观察动态响应

    依赖注入设计：
      不直接 import main，而是通过构造函数注入
      data_provider  : 获取指定节点最新数据的函数
      queue_provider : 获取指定节点队列尾部数据的函数
      mqtt_publisher : 向指定节点发布MQTT指令的函数
      这样 test_bench 和 main 之间没有直接依赖，解决循环导入
    """

    def __init__(
        self,
        data_provider:  Optional[Callable] = None,
        queue_provider: Optional[Callable] = None,
        mqtt_publisher: Optional[Callable] = None,
    ):
        # ==========================================
        # 依赖注入：由 main.py 在 lifespan 中注入
        # ==========================================
        self._data_provider  = data_provider   # fn(node_id) -> dict
        self._queue_provider = queue_provider  # fn(node_id, count) -> list
        self._mqtt_publisher = mqtt_publisher  # fn(node_id, command, params) -> bool

        # ==========================================
        # 运行状态
        # ==========================================
        self.is_running        = False
        self.current_case_name = "无"
        self.progress          = 0
        self.total_cases       = 0
        self.target_node_id    = "ENV_SIM_001"  # 当前测试目标节点

        # ==========================================
        # 结果与日志
        # ==========================================
        self.results = []
        self.logs    = deque(maxlen=500)   # 限制最大条数，防止内存无限增长

        # ==========================================
        # 线程控制
        # ==========================================
        self._thread    = None
        self._stop_flag = False   # 强制停止标志

        # ==========================================
        # 用例注册中心
        # ==========================================
        self.registry = self._build_registry()

    # ==========================================
    # 依赖注入接口
    # 由 main.py 在初始化后调用
    # ==========================================
    def inject_dependencies(
        self,
        data_provider:  Callable,
        queue_provider: Callable,
        mqtt_publisher: Callable,
    ):
        """
        注入运行时依赖
        在 main.py 的 lifespan 中调用：

        executor.inject_dependencies(
            data_provider  = lambda node_id: get_node_latest(node_id),
            queue_provider = lambda node_id, count: get_node_queue_tail(node_id, count),
            mqtt_publisher = lambda node_id, cmd, params: publish_control(node_id, cmd, params),
        )
        """
        self._data_provider  = data_provider
        self._queue_provider = queue_provider
        self._mqtt_publisher = mqtt_publisher
        logger.info("[TestBench] 依赖注入完成")

    # ==========================================
    # 内部工具方法
    # ==========================================
    def _log(self, msg: str):
        """记录日志（同时输出到logger和内部日志队列）"""
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        log_str   = f"[{timestamp}] {msg}"
        logger.info(log_str)
        self.logs.append(log_str)

    def _send_command(self, command: str, params: dict) -> bool:
        """
        向当前目标节点下发控制指令
        通过注入的 mqtt_publisher 发送，不直接依赖 main
        """
        if not self._mqtt_publisher:
            self._log("错误：MQTT发布函数未注入，无法下发指令")
            return False
        try:
            result = self._mqtt_publisher(
                self.target_node_id,
                command,
                params
            )
            self._log(f"-> 下发指令: {command} | 参数: {params} | 节点: {self.target_node_id}")
            return result
        except Exception as e:
            self._log(f"错误：指令下发失败: {e}")
            return False

    def _wait(self, seconds: float):
        """
        可中断的等待
        每0.1秒检查一次停止标志，支持强制停止
        """
        steps = int(seconds * 10)
        for _ in range(steps):
            if self._stop_flag:
                raise InterruptedError("测试被用户强制停止")
            time.sleep(0.1)

    def _get_latest(self) -> dict:
        """获取当前目标节点的最新传感器数据"""
        if not self._data_provider:
            self._log("错误：数据获取函数未注入")
            return {}
        try:
            return self._data_provider(self.target_node_id)
        except Exception as e:
            self._log(f"错误：获取最新数据失败: {e}")
            return {}

    def _get_queue_tail(self, count: int = 10) -> list:
        """获取当前目标节点队列尾部的最近N条数据"""
        if not self._queue_provider:
            self._log("错误：队列获取函数未注入")
            return []
        try:
            return self._queue_provider(self.target_node_id, count)
        except Exception as e:
            self._log(f"错误：获取队列数据失败: {e}")
            return []

    # ==========================================
    # 用例注册中心
    # ==========================================
    def _build_registry(self) -> dict:
        """
        构建用例元数据注册中心

        测试用例覆盖四个维度（论文理论框架）：
          1. 静态性能：精度、稳定性          ← case_static_accuracy（新增）
          2. 动态性能：响应时间、超调量      ← case_temp_step
          3. 故障诊断：FDI能力              ← case_fault_diagnosis
          4. 场景适应：复杂工况抗扰          ← case_scenario_anti
          附加. 安全通信：数据完整性验证     ← case_aes_tamper
        """
        return {
            # ------------------------------------------
            # 静态性能测试（新增）
            # 验证传感器在稳定工况下的精度和一致性
            # ------------------------------------------
            "case_static_accuracy": {
                "name":           "传感器静态精度一致性测试",
                "type":           "static_performance",
                "default_params": {
                    "stable_duration":  10.0,  # 稳定采集时长（秒）
                    "check_samples":    20,    # 采样数量
                    "max_std_dev":       1.0,  # 允许的最大标准差（℃）
                    "expected_temp":    25.0,  # 基准期望温度（℃）
                    "max_bias":          2.0,  # 允许的最大偏差（℃）
                },
                "executor": self._case_0_static_accuracy,
            },

            # ------------------------------------------
            # 动态性能测试
            # 验证传感器对温度阶跃的响应速度和超调量
            # ------------------------------------------
            "case_temp_step": {
                "name":           "极限温度阶跃响应测试",
                "type":           "dynamic_performance",
                "default_params": {
                    "base_temp":      20.0,   # 起始基准温度（℃）
                    "target_temp":    80.0,   # 阶跃目标温度（℃）
                    "timeout":        15.0,   # 响应超时时间（秒）
                    "max_overshoot":   2.0,   # 允许的最大超调量（℃）
                },
                "executor": self._case_1_temp_step_response,
            },

            # ------------------------------------------
            # 故障诊断测试
            # 验证系统的故障识别与诊断（FDI）能力
            # ------------------------------------------
            "case_fault_diagnosis": {
                "name":           "硬件断路故障诊断测试",
                "type":           "fault_injection",
                "default_params": {
                    "target":           "in_car_temp",  # 故障注入目标传感器
                    "fault_type":       "OPEN_CIRCUIT", # 故障类型
                    "capture_timeout":   5.0,           # 捕获超时时间（秒）
                },
                "executor": self._case_2_hardware_fault_diagnosis,
            },

            # ------------------------------------------
            # 场景适应测试
            # 验证复杂工况下传感器数据的跟随性
            # ------------------------------------------
            "case_scenario_anti": {
                "name":           "复杂工况动态抗扰测试",
                "type":           "scenario_follow",
                "default_params": {
                    "scenario_name":  "tunnel_following", # 预设工况名
                    "wait_time":       15.0,              # 等待工况稳定时长（秒）
                    "check_samples":   10,                # 统计均值所需样本数
                    "pm25_threshold":  50.0,              # PM2.5判定阈值（μg/m³）
                },
                "executor": self._case_3_complex_scenario_anti_interference,
            },

            # ------------------------------------------
            # 安全通信测试
            # 验证AES-CBC+HMAC的抗篡改能力
            # ------------------------------------------
            "case_aes_tamper": {
                "name":           "安全通信链路抗篡改测试",
                "type":           "security",
                "default_params": {},  # 无自定义参数
                "executor": self._case_4_aes_tamper_resistance,
            },
        }

    # ==========================================
    # 测试用例实现
    # ==========================================

    def _case_0_static_accuracy(self, params: dict):
        """
        用例0：传感器静态精度一致性测试（新增）

        测试逻辑：
          1. 下发指令将传感器稳定在基准温度
          2. 持续采集N个样本
          3. 计算均值、标准差、最大偏差
          4. 判定是否满足精度要求

        对应论文中"静态性能"测试维度
        """
        case_name = (
            f"静态精度测试 "
            f"(基准: {params['expected_temp']}℃, "
            f"采样: {params['check_samples']}次)"
        )
        self.current_case_name = case_name
        self._log(f"========== 开始执行: {case_name} ==========")
        start_time = time.time()
        result = {
            "case_id": "case_static_accuracy",
            "case":    case_name,
            "status":  "PASS",
            "details": [],
        }

        try:
            # 1. 下发基准温度指令，让传感器稳定
            self._send_command(
                "override_value",
                {"target": "in_car_temp", "value": params["expected_temp"]}
            )
            self._log(f"已下发基准温度指令: {params['expected_temp']}℃，等待稳定...")
            self._wait(params["stable_duration"])

            # 2. 采集样本
            samples = []
            sample_count = int(params["check_samples"])
            for i in range(sample_count):
                if self._stop_flag:
                    raise InterruptedError("测试被强制停止")
                data = self._get_latest()
                temp = data.get("in_car_temp")
                if temp is not None:
                    samples.append(temp)
                time.sleep(0.3)

            if len(samples) < 5:
                result["status"] = "FAIL"
                result["details"].append(
                    f"有效样本不足：仅采集到 {len(samples)} 个"
                )
                return

            # 3. 统计分析
            mean_val  = sum(samples) / len(samples)
            variance  = sum((x - mean_val) ** 2 for x in samples) / len(samples)
            std_dev   = variance ** 0.5
            max_val   = max(samples)
            min_val   = min(samples)
            max_bias  = max(abs(mean_val - params["expected_temp"]),
                            abs(max_val  - params["expected_temp"]),
                            abs(min_val  - params["expected_temp"]))

            self._log(
                f"静态分析结果: 均值={mean_val:.2f}℃, "
                f"标准差={std_dev:.3f}℃, "
                f"最大偏差={max_bias:.2f}℃"
            )

            # 4. 判定标准差
            if std_dev > params["max_std_dev"]:
                result["status"] = "FAIL"
                result["details"].append(
                    f"稳定性不足：标准差 {std_dev:.3f}℃ "
                    f"> 允许值 {params['max_std_dev']}℃"
                )
            else:
                result["details"].append(
                    f"稳定性良好：标准差 {std_dev:.3f}℃ "
                    f"≤ 允许值 {params['max_std_dev']}℃"
                )

            # 5. 判定最大偏差
            if max_bias > params["max_bias"]:
                result["status"] = "FAIL"
                result["details"].append(
                    f"精度不足：最大偏差 {max_bias:.2f}℃ "
                    f"> 允许值 {params['max_bias']}℃"
                )
            else:
                result["details"].append(
                    f"精度达标：最大偏差 {max_bias:.2f}℃ "
                    f"≤ 允许值 {params['max_bias']}℃"
                )

            result["details"].append(
                f"样本统计: 均值={mean_val:.2f}℃, "
                f"最大={max_val:.2f}℃, 最小={min_val:.2f}℃, "
                f"共{len(samples)}个样本"
            )

        except InterruptedError as e:
            result["status"] = "INTERRUPTED"
            result["details"].append(str(e))
        except Exception as e:
            result["status"] = "ERROR"
            result["details"].append(f"用例执行异常: {str(e)}")
        finally:
            self._send_command("clear_fault", {})
            result["duration"] = round(time.time() - start_time, 2)
            self.results.append(result)
            self._log(
                f"========== 结束执行: {case_name} "
                f"[{result['status']}] =========="
            )

    def _case_1_temp_step_response(self, params: dict):
        """
        用例1：极限温度阶跃响应测试

        测试逻辑：
          1. 建立基准温度
          2. 触发阶跃指令
          3. 捕获响应时间和超调量
          4. 判定是否满足动态性能指标
        """
        case_name = f"阶跃响应测试 (目标: {params['target_temp']}℃)"
        self.current_case_name = case_name
        self._log(f"========== 开始执行: {case_name} ==========")
        start_time = time.time()
        result = {
            "case_id": "case_temp_step",
            "case":    case_name,
            "status":  "PASS",
            "details": [],
        }

        try:
            # 1. 建立基准
            self._send_command(
                "override_value",
                {"target": "in_car_temp", "value": params["base_temp"]}
            )
            self._log(f"建立基准温度: {params['base_temp']}℃，等待稳定...")
            self._wait(8)

            # 2. 触发阶跃
            self._send_command(
                "override_value",
                {"target": "in_car_temp", "value": params["target_temp"]}
            )
            self._log(f"已下发阶跃指令 -> {params['target_temp']}℃")

            # 3. 捕获响应
            max_temp_seen  = self._get_latest().get("in_car_temp", 0.0)
            reached_target = False
            start_measure  = time.time()
            target_90      = params["target_temp"] * 0.9  # 90%响应判定点

            while time.time() - start_measure < params["timeout"]:
                if self._stop_flag:
                    raise InterruptedError("测试被强制停止")
                data = self._get_latest()
                temp = data.get("in_car_temp", 0.0)
                max_temp_seen = max(max_temp_seen, temp)

                if temp >= target_90 and not reached_target:
                    response_time = time.time() - start_measure
                    self._log(
                        f"到达目标区域 {target_90:.1f}℃ "
                        f"(响应时间: {response_time:.2f}s)"
                    )
                    reached_target = True
                    break
                time.sleep(0.1)

            # 4. 判定结果
            if not reached_target:
                result["status"] = "FAIL"
                result["details"].append(
                    f"响应超时：未在 {params['timeout']}s 内达到目标"
                )

            overshoot = max_temp_seen - params["target_temp"]
            if overshoot > params["max_overshoot"]:
                result["status"] = "FAIL"
                result["details"].append(
                    f"超调量过大：峰值 {max_temp_seen:.1f}℃ "
                    f"(超调 {overshoot:.1f}℃ > 允许 {params['max_overshoot']}℃)"
                )
            else:
                result["details"].append(
                    f"动态响应良好 (超调: {overshoot:.1f}℃ "
                    f"≤ 允许 {params['max_overshoot']}℃)"
                )

        except InterruptedError as e:
            result["status"] = "INTERRUPTED"
            result["details"].append(str(e))
        except Exception as e:
            result["status"] = "ERROR"
            result["details"].append(f"用例执行异常: {str(e)}")
        finally:
            self._send_command("clear_fault", {})
            result["duration"] = round(time.time() - start_time, 2)
            self.results.append(result)
            self._log(
                f"========== 结束执行: {case_name} "
                f"[{result['status']}] =========="
            )

    def _case_2_hardware_fault_diagnosis(self, params: dict):
        """
        用例2：硬件断路故障诊断测试

        测试逻辑：
          1. 注入指定类型的硬件故障
          2. 等待系统上报故障状态
          3. 验证故障码是否与预期一致
          4. 判定FDI（故障检测与隔离）能力
        """
        case_name = (
            f"故障诊断测试 "
            f"(目标: {params['target']} - {params['fault_type']})"
        )
        self.current_case_name = case_name
        self._log(f"========== 开始执行: {case_name} ==========")
        start_time = time.time()
        result = {
            "case_id": "case_fault_diagnosis",
            "case":    case_name,
            "status":  "PASS",
            "details": [],
        }

        try:
            # 1. 清除历史故障，确保干净的初始状态
            self._send_command("clear_fault", {})
            self._wait(2)

            # 2. 注入故障
            self._send_command(
                "inject_fault",
                {"target": params["target"], "fault_type": params["fault_type"]}
            )

            # 3. 等待系统上报故障
            fault_captured      = False
            captured_fault_code = ""
            expected_code       = (
                f"{params['target'].upper()}_{params['fault_type']}"
            )
            start_capture = time.time()

            while time.time() - start_capture < params["capture_timeout"]:
                if self._stop_flag:
                    raise InterruptedError("测试被强制停止")
                data = self._get_latest()
                if data.get("status") == "FAULT":
                    fault_captured      = True
                    captured_fault_code = data.get("fault_code", "")
                    self._log(f"成功捕获故障上报: {captured_fault_code}")
                    break
                time.sleep(0.1)

            # 4. 判定结果
            if not fault_captured:
                result["status"] = "FAIL"
                result["details"].append(
                    f"诊断失效：{params['capture_timeout']}s 内未收到故障状态"
                )
            elif captured_fault_code != expected_code:
                result["status"] = "FAIL"
                result["details"].append(
                    f"故障码错误：预期 {expected_code}，"
                    f"实际 {captured_fault_code}"
                )
            else:
                result["details"].append(
                    f"FDI逻辑准确，故障识别及时 "
                    f"(故障码: {captured_fault_code})"
                )

        except InterruptedError as e:
            result["status"] = "INTERRUPTED"
            result["details"].append(str(e))
        except Exception as e:
            result["status"] = "ERROR"
            result["details"].append(f"用例执行异常: {str(e)}")
        finally:
            self._send_command("clear_fault", {})
            result["duration"] = round(time.time() - start_time, 2)
            self.results.append(result)
            self._log(
                f"========== 结束执行: {case_name} "
                f"[{result['status']}] =========="
            )

    def _case_3_complex_scenario_anti_interference(self, params: dict):
        """
        用例3：复杂工况动态抗扰测试

        测试逻辑：
          1. 切换到指定复杂工况（如隧道跟车）
          2. 等待传感器数据跟随工况稳定
          3. 统计PM2.5均值判定工况是否生效
          4. 验证传感器在复杂环境下的适应能力
        """
        case_name = f"抗扰测试 (工况: {params['scenario_name']})"
        self.current_case_name = case_name
        self._log(f"========== 开始执行: {case_name} ==========")
        start_time = time.time()
        result = {
            "case_id": "case_scenario_anti",
            "case":    case_name,
            "status":  "PASS",
            "details": [],
        }

        try:
            # 1. 切换工况
            self._send_command(
                "set_scenario",
                {"scenario": params["scenario_name"]}
            )
            self._log(
                f"已切换工况: {params['scenario_name']}，"
                f"等待 {params['wait_time']}s 稳定..."
            )
            self._wait(params["wait_time"])

            # 2. 采集稳态数据
            tail_data = self._get_queue_tail(int(params["check_samples"]))

            if len(tail_data) < 5:
                result["status"] = "FAIL"
                result["details"].append(
                    f"数据采集不足：仅有 {len(tail_data)} 条"
                )
                return

            # 3. 统计分析（以PM2.5为主要判定指标）
            avg_pm25 = sum(d.get("pm25", 0) for d in tail_data) / len(tail_data)
            avg_co2  = sum(d.get("co2", 0) for d in tail_data) / len(tail_data)
            self._log(
                f"工况稳态分析: "
                f"平均PM2.5={avg_pm25:.1f}μg/m³, "
                f"平均CO2={avg_co2:.1f}ppm"
            )

            # 4. 判定工况是否生效（PM2.5超过阈值说明污染工况已生效）
            if avg_pm25 < params["pm25_threshold"]:
                result["status"] = "FAIL"
                result["details"].append(
                    f"工况未生效：PM2.5均值 {avg_pm25:.1f}μg/m³ "
                    f"< 阈值 {params['pm25_threshold']}μg/m³"
                )
            else:
                result["details"].append(
                    f"工况跟随正常 "
                    f"(PM2.5均值: {avg_pm25:.1f}μg/m³, "
                    f"CO2均值: {avg_co2:.1f}ppm)"
                )

        except InterruptedError as e:
            result["status"] = "INTERRUPTED"
            result["details"].append(str(e))
        except Exception as e:
            result["status"] = "ERROR"
            result["details"].append(f"用例执行异常: {str(e)}")
        finally:
            self._send_command("clear_fault", {})
            result["duration"] = round(time.time() - start_time, 2)
            self.results.append(result)
            self._log(
                f"========== 结束执行: {case_name} "
                f"[{result['status']}] =========="
            )

    def _case_4_aes_tamper_resistance(self, params: dict):
        """
        用例4：安全通信链路抗篡改测试

        测试逻辑：
          构造多种被篡改的数据包，尝试通过解密验证
          验证AES-CBC + HMAC签名机制能否有效拦截
          每种篡改场景独立判定，全部拦截才算PASS
        """
        case_name = "安全通信链路抗篡改测试"
        self.current_case_name = case_name
        self._log(f"========== 开始执行: {case_name} ==========")
        start_time = time.time()
        result = {
            "case_id": "case_aes_tamper",
            "case":    case_name,
            "status":  "PASS",
            "details": [],
        }

        try:
            # 多种篡改场景，全部需要被拦截
            tamper_cases = [
                ("随机伪造字符串",        "dGVzdF9hbHRlcmVkX3N0cmluZw=="),
                ("空字符串",              ""),
                ("合法Base64但内容错误",  "aGVsbG8gd29ybGQ="),
                ("长度不足（截断攻击）",  "YWJjZA=="),
            ]

            all_blocked = True
            for desc, fake_payload in tamper_cases:
                self._log(f"测试篡改场景: [{desc}]")
                decrypt_result = decrypt_data(fake_payload)

                if decrypt_result is not None:
                    all_blocked = False
                    result["details"].append(
                        f"❌ 防线失效：场景[{desc}] 绕过了安全校验"
                    )
                    self._log(f"警告：场景[{desc}] 未被拦截！")
                else:
                    result["details"].append(
                        f"✅ 已拦截：场景[{desc}]"
                    )
                    self._log(f"已拦截：场景[{desc}]")

            if not all_blocked:
                result["status"] = "FAIL"
                result["details"].append(
                    "安全防线存在漏洞，部分篡改数据未被拦截"
                )
            else:
                result["details"].append(
                    f"安全防线完整：全部 {len(tamper_cases)} 种篡改场景均被拦截"
                )
                self._log("AES-CBC + HMAC 抗篡改验证通过 ✅")

        except Exception as e:
            result["status"] = "ERROR"
            result["details"].append(f"用例执行异常: {str(e)}")
        finally:
            result["duration"] = round(time.time() - start_time, 2)
            self.results.append(result)
            self._log(
                f"========== 结束执行: {case_name} "
                f"[{result['status']}] =========="
            )

    # ==========================================
    # 调度引擎
    # ==========================================
    def _run_suite(self, selected_cases_config: list, node_id: str):
        """
        按顺序执行选中的测试用例

        :param selected_cases_config: 用例配置列表
            [
                {"id": "case_temp_step", "params": {"target_temp": 85.0}},
                {"id": "case_aes_tamper", "params": {}}
            ]
        :param node_id: 目标节点ID
        """
        self.is_running        = True
        self._stop_flag        = False
        self.target_node_id    = node_id
        self.results           = []
        self.logs              = deque(maxlen=500)
        self.total_cases       = len(selected_cases_config)
        self.progress          = 0

        self._log("=" * 50)
        self._log(f"台架测试启动 | 目标节点: {node_id} | 用例数: {self.total_cases}")
        self._log("=" * 50)

        for case_config in selected_cases_config:
            # 检查停止标志
            if self._stop_flag:
                self._log("收到停止信号，终止后续用例执行")
                break

            case_id      = case_config.get("id")
            custom_params = case_config.get("params", {})

            # 从注册中心查找用例
            case_meta = self.registry.get(case_id)
            if not case_meta:
                self._log(f"警告：找不到用例 ID '{case_id}'，跳过")
                self.progress += 1
                continue

            # 合并参数（自定义参数覆盖默认参数）
            final_params = case_meta["default_params"].copy()
            final_params.update(custom_params)

            # 执行用例
            executor_func = case_meta["executor"]
            try:
                executor_func(final_params)
            except Exception as e:
                self._log(f"致命错误：执行 {case_id} 时发生未捕获异常: {e}")

            self.progress += 1

            # 用例间隔（可被停止标志打断）
            if not self._stop_flag:
                try:
                    self._wait(2)
                except InterruptedError:
                    break

        self.is_running        = False
        self.current_case_name = "测试完成" if not self._stop_flag else "已停止"
        self._log("=" * 50)
        self._log(
            f"测试结束 | "
            f"完成: {self.progress}/{self.total_cases} | "
            f"{'正常结束' if not self._stop_flag else '强制停止'}"
        )
        self._log("=" * 50)

    # ==========================================
    # 公开接口
    # ==========================================
    def start(self, config=None, node_id: str = "ENV_SIM_001") -> bool:
        """
        启动测试套件

        :param config:  用例配置列表
        :param node_id: 目标节点ID，默认模拟器节点
                        ESP32接入后可传入 "ESP32_001"
        :return: True=成功启动，False=已在运行或配置为空
        """
        if self.is_running:
            logger.warning("[TestBench] 台架正在运行中，拒绝重复启动")
            return False

        if not config:
            logger.warning("[TestBench] 用例配置为空，拒绝启动")
            return False

        self._thread = threading.Thread(
            target=self._run_suite,
            args=(config, node_id),
            daemon=True
        )
        self._thread.start()
        return True

    def stop(self):
        """
        发送强制停止信号
        当前用例执行完毕后停止，不会强制杀死线程
        """
        if self.is_running:
            self._stop_flag = True
            logger.info("[TestBench] 已发送停止信号")


# ==========================================
# 全局执行器实例
# 依赖在 main.py 的 lifespan 中注入
# ==========================================
executor = TestBenchExecutor()
