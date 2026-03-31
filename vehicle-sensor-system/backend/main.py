# backend/main.py

import json
import threading
import logging
import sys
import os
import time
from collections import deque

from fastapi import FastAPI
from paho.mqtt import client as mqtt_client
from fastapi.middleware.cors import CORSMiddleware

# 引入解密工具
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crypto_utils import decrypt_data

# 引入测试引擎
from test_bench import executor as bench_executor
from fastapi.responses import JSONResponse

# ================= 配置区域 =================
BROKER = 'broker.emqx.io'
PORT = 1883
TOPIC = "vcar/sensors/environment/data"
CONTROL_TOPIC = "vcar/sensors/environment/control"
CLIENT_ID = "Backend_TestBench_V1"
# ===========================================

# --- 配置日志 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TestBench")

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 核心数据层：内存数据池（取代直接入库）
# ==========================================
# 线程锁，保证 FastAPI 线程和 MQTT 线程读写安全
data_lock = threading.Lock()

# 最新单条数据字典（供测试用例实时读取）
latest_sensor_data = {
    "raw_dict": None,  # 完整的原始 JSON 字典
    "in_car_temp": 0.0,
    "out_car_temp": 0.0,
    "humidity": 0.0,
    "pm25": 0.0,
    "co2": 0.0,
    "status": "NORMAL",
    "fault_code": "NONE",
    "latency_ms": 0
}

# 滑动窗口数据队列（保留最近 100 条，供趋势分析使用）
DATA_QUEUE_MAX_LEN = 100
data_queue = deque(maxlen=DATA_QUEUE_MAX_LEN)

# 全局 MQTT 客户端实例（供后续 API 下发控制指令使用）
mqtt_client_instance = None


# ==========================================


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"[数据采集层] 成功连接到 MQTT Broker")
        client.subscribe(TOPIC)
        client.subscribe(CONTROL_TOPIC)  # 顺便订阅控制主题的回显(可选)
    else:
        logger.error(f"[数据采集层] 连接失败，代码: {rc}")


def on_message(client, userdata, msg):
    """
    纯粹的数据采集与解密逻辑，绝对不包含任何业务判定和数据库操作
    """
    global latest_sensor_data

    # 忽略控制主题的自发回显
    if msg.topic == CONTROL_TOPIC:
        return

    try:
        # 1. 安全解密
        encrypted_payload = msg.payload.decode()
        decrypted_json = decrypt_data(encrypted_payload)
        if decrypted_json is None:
            logger.error("[数据采集层] 解密失败，丢弃数据包")
            return

        data = json.loads(decrypted_json)
        sensor_data = data.get('data', {})

        # 2. 提取核心数值
        parsed_item = {
            "timestamp": data.get('timestamp'),
            "in_car_temp": sensor_data.get('in_car_temp', 0.0),
            "out_car_temp": sensor_data.get('out_car_temp', 0.0),
            "humidity": sensor_data.get('humidity', 0.0),
            "pm25": sensor_data.get('pm25', 0.0),
            "co2": sensor_data.get('co2', 0.0),
            "status": data.get('status', 'NORMAL'),
            "fault_code": data.get('fault_code', 'NONE'),
            "latency_ms": int(time.time() * 1000 - data.get('send_time', time.time() * 1000))
        }

        # 3. 线程安全地更新内存数据池
        with data_lock:
            latest_sensor_data["raw_dict"] = data
            latest_sensor_data.update(parsed_item)
            data_queue.append(parsed_item)

    except json.JSONDecodeError:
        logger.error("[数据采集层] JSON解析失败")
    except Exception as e:
        logger.error(f"[数据采集层] 未知错误: {e}")


def mqtt_thread_task():
    global mqtt_client_instance
    client = mqtt_client.Client(CLIENT_ID)
    mqtt_client_instance = client
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_forever()
    except Exception as e:
        logger.error(f"[数据采集层] MQTT 线程异常退出: {e}")


@app.on_event("startup")
def startup_event():
    logger.info("[系统启动] 正在初始化数据采集线程...")
    thread = threading.Thread(target=mqtt_thread_task, daemon=True)
    thread.start()


# --- 临时调试接口 (用于验证第一步是否成功) ---
@app.get("/api/debug/pool")
def get_pool_status():
    """查看内存数据池的实时状态"""
    with data_lock:
        queue_len = len(data_queue)
        # 取队列最后一条（最新）
        latest_in_queue = data_queue[-1] if queue_len > 0 else None
    return {
        "queue_length": queue_len,
        "max_queue_length": DATA_QUEUE_MAX_LEN,
        "latest_data_snapshot": latest_sensor_data,
        "latest_in_queue": latest_in_queue
    }


@app.get("/")
def read_root():
    return {"message": "台架测试系统 - 数据采集层运行中"}

@app.post("/api/bench/run")
def run_bench():
    """触发台架自动化测试"""
    if bench_executor.is_running:
        return {"message": "测试正在执行中", "status": "error"}
    bench_executor.start()
    return {"message": "台架测试已触发", "status": "success"}

@app.get("/api/bench/status")
def get_bench_status():
    """获取测试执行器实时状态"""
    return {
        "is_running": bench_executor.is_running,
        "current_case": bench_executor.current_case_name,
        "progress": f"{bench_executor.progress}/{bench_executor.total_cases}",
        "results_summary": [{"case": r["case"], "status": r["status"]} for r in bench_executor.results]
    }

@app.get("/api/bench/logs")
def get_bench_logs():
    """获取实时控制台日志"""
    # 返回最后 50 条日志
    return {"logs": bench_executor.logs[-50:]}

@app.get("/api/bench/report")
def get_bench_report():
    """获取最终详细报告数据"""
    if bench_executor.is_running:
        return {"message": "测试尚未结束", "status": "error"}
    return {
        "status": "success",
        "total": bench_executor.total_cases,
        "pass_count": sum(1 for r in bench_executor.results if r["status"] == "PASS"),
        "fail_count": sum(1 for r in bench_executor.results if r["status"] == "FAIL"),
        "details": bench_executor.results
    }