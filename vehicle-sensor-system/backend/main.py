# backend/main.py

import json
import threading
import logging
import sys
import os
import time
import datetime

from fastapi import FastAPI
from paho.mqtt import client as mqtt_client
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

# 引入解密工具和测试引擎
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crypto_utils import decrypt_data, encrypt_data
from test_engine import run_content_test

# 导入数据库模块
from database import SessionLocal, engine, Base
from models import SensorData
from pydantic import BaseModel

# ================= 配置区域 =================
BROKER = 'broker.emqx.io'
PORT = 1883
TOPIC = "vcar/sensors/environment/data"  # 新协议 Topic
CLIENT_ID = "Backend_Server_V2"

# --- 全局状态：用于丢包检测 ---
device_last_timestamp = {}
# --- 全局状态：用于测试任务管理 ---
test_session = {
    "is_active": False,
    "start_time": None,
    "total_count": 0,
    "abnormal_count": 0,
    "total_latency": 0,
}
# --- 全局状态：用于突变检测 ---
device_last_values = {}
# --- 全局状态：动态测试规则配置 ---
test_config = {
    "temp_min": -40.0,
    "temp_max": 85.0,
    "hum_min": 0.0,
    "hum_max": 100.0,
    "temp_change_limit": 5.0,
    "pm25_change_limit": 30.0,
    "pm25_max": 75.0,
    "co2_max": 1000.0,
    "lost_timeout": 5
}
# ===========================================

# --- 配置日志 ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VehicleSystem")

# --- 初始化数据库 ---
Base.metadata.create_all(bind=engine)
logger.info("[INFO] 数据库表结构检查完成")

app = FastAPI()
# --- 配置跨域 ---
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- MQTT 消息处理 ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"[INFO] <Backend> 成功连接到 MQTT Broker，订阅主题: {TOPIC}")
        client.subscribe(TOPIC)
    else:
        logger.error(f"[ERROR] <Backend> 连接失败，代码: {rc}")


def on_message(client, userdata, msg):
    """核心回调：解密 -> 硬件自检 -> 丢包 -> 突变 -> 内容校验 -> 加密存储"""
    global device_last_timestamp, device_last_values, test_session, test_config

    try:
        # ================= 1. 安全模块：解密 =================
        encrypted_payload = msg.payload.decode()
        decrypted_json = decrypt_data(encrypted_payload)
        if decrypted_json is None:
            logger.error("[ERROR] <Security> 解密失败！数据可能被篡改。")
            return

        data = json.loads(decrypted_json)

        # ================= 2. 解析新协议字段 =================
        current_sensor_id = data.get('sensor_id', 'UNKNOWN')
        current_timestamp = data.get('timestamp')  # 毫秒级时间戳
        sensor_data = data.get('data', {})
        current_status = data.get('status', 'NORMAL')
        current_fault_code = data.get('fault_code', 'NONE')

        in_car_temp = sensor_data.get('in_car_temp')
        pm25 = sensor_data.get('pm25')

        # ================= 3. 传感器硬件级故障判定 =================
        hw_errors = []
        if current_status == "FAULT":
            hw_errors.append(f"硬件自检故障: {current_fault_code}")

        # ================= 4. 通信连续性检测 (丢包) =================
        continuity_errors = []
        if current_sensor_id in device_last_timestamp:
            last_ts = device_last_timestamp[current_sensor_id]
            diff_ms = current_timestamp - last_ts
            if diff_ms > test_config["lost_timeout"] * 1000:
                continuity_errors.append(f"通信不连续: 间隔{diff_ms / 1000:.1f}秒")
        device_last_timestamp[current_sensor_id] = current_timestamp

        # ================= 5. 数据稳定性检测 (突变) =================
        stability_errors = []
        if current_sensor_id in device_last_values:
            last_vals = device_last_values[current_sensor_id]

            if in_car_temp is not None and last_vals.get('in_car_temp') is not None:
                if abs(in_car_temp - last_vals['in_car_temp']) > test_config["temp_change_limit"]:
                    stability_errors.append(f"车内温突变: {last_vals['in_car_temp']}℃ -> {in_car_temp}℃")

            if pm25 is not None and last_vals.get('pm25') is not None:
                if abs(pm25 - last_vals['pm25']) > test_config["pm25_change_limit"]:
                    stability_errors.append(f"PM2.5突变: {last_vals['pm25']} -> {pm25}")

        device_last_values[current_sensor_id] = sensor_data.copy()

        # ================= 6. 自动化测试引擎 (内容合规校验) =================
        is_abnormal_content, error_msg_content = run_content_test(sensor_data, test_config)

        # ================= 7. 合并所有的错误信息 =================
        all_errors = hw_errors + continuity_errors + stability_errors
        if error_msg_content:
            all_errors.append(error_msg_content)

        final_is_abnormal = len(all_errors) > 0
        final_error_msg = "; ".join(all_errors)

        # ================= 8. 计算延迟 =================
        send_time = data.get('send_time', 0)
        current_time_ms = time.time() * 1000
        latency_ms = int(current_time_ms - send_time) if send_time else 0

        # ================= 9. 测试任务管理与入库 =================
        if test_session["is_active"]:
            test_session["total_count"] += 1
            if final_is_abnormal:
                test_session["abnormal_count"] += 1
            test_session["total_latency"] += latency_ms

            db = SessionLocal()
            try:
                def enc(val):
                    return encrypt_data(str(val)) if val is not None else None

                db_data = SensorData(
                    sensor_id=current_sensor_id,
                    in_car_temp=enc(in_car_temp),
                    out_car_temp=enc(sensor_data.get('out_car_temp')),
                    humidity=enc(sensor_data.get('humidity')),
                    pm25=enc(pm25),
                    co2=enc(sensor_data.get('co2')),
                    status=current_status,
                    fault_code=current_fault_code,
                    latency=latency_ms,
                    is_abnormal=final_is_abnormal,
                    error_msg=final_error_msg
                )
                db.add(db_data)
                db.commit()

                status_log = "x 异常" if final_is_abnormal else "v 正常"
                logger.info(
                    f"[测试中] 车内:{in_car_temp}℃ | PM2.5:{pm25} | 延迟:{latency_ms}ms | 判定: {status_log} | {final_error_msg or ''}")

            except Exception as db_err:
                logger.error(f"[ERROR] 数据库写入错误: {db_err}")
            finally:
                db.close()
        else:
            logger.info(f"[待机] 忽略数据: 车内{in_car_temp}℃")

    except json.JSONDecodeError:
        logger.error("[ERROR] 数据解析失败：非JSON格式")
    except Exception as e:
        logger.error(f"[ERROR] 处理消息时发生未知错误: {e}")


def mqtt_thread_task():
    client = mqtt_client.Client(CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_forever()
    except Exception as e:
        logger.error(f"[ERROR] MQTT 线程异常: {e}")


@app.on_event("startup")
def startup_event():
    logger.info("[INFO] 后端服务启动，正在启动 MQTT 监听线程...")
    thread = threading.Thread(target=mqtt_thread_task, daemon=True)
    thread.start()


# --- API 接口 ---
@app.get("/")
def read_root():
    return {"message": "车载环境传感器测试系统运行中"}


def safe_decrypt(val):
    try:
        return float(decrypt_data(val)) if val else 0.0
    except:
        return 0.0


@app.get("/api/realtime")
def get_realtime():
    db = SessionLocal()
    try:
        data = db.query(SensorData).order_by(SensorData.create_time.desc()).first()
        if not data: return None
        return {
            "id": data.id, "sensor_id": data.sensor_id,
            "in_car_temp": safe_decrypt(data.in_car_temp),
            "out_car_temp": safe_decrypt(data.out_car_temp),
            "humidity": safe_decrypt(data.humidity),
            "pm25": safe_decrypt(data.pm25),
            "co2": safe_decrypt(data.co2),
            "status": data.status, "fault_code": data.fault_code,
            "latency": data.latency, "is_abnormal": data.is_abnormal,
            "error_msg": data.error_msg, "create_time": data.create_time
        }
    finally:
        db.close()


@app.get("/api/history")
def get_history(limit: int = 20):
    db = SessionLocal()
    try:
        data_list = db.query(SensorData).order_by(SensorData.create_time.desc()).limit(limit).all()
        result = []
        for item in data_list:
            result.append({
                "id": item.id, "sensor_id": item.sensor_id,
                "in_car_temp": safe_decrypt(item.in_car_temp),
                "out_car_temp": safe_decrypt(item.out_car_temp),
                "humidity": safe_decrypt(item.humidity),
                "pm25": safe_decrypt(item.pm25),
                "co2": safe_decrypt(item.co2),
                "status": item.status, "fault_code": item.fault_code,
                "latency": item.latency, "is_abnormal": item.is_abnormal,
                "error_msg": item.error_msg, "create_time": item.create_time
            })
        return result
    finally:
        db.close()


# --- 测试任务管理接口 ---
@app.post("/api/test/start")
def start_test():
    if test_session["is_active"]: return {"message": "测试已在进行中", "status": "error"}
    test_session["is_active"] = True
    test_session["start_time"] = datetime.datetime.now()
    test_session["total_count"] = 0
    test_session["abnormal_count"] = 0
    test_session["total_latency"] = 0
    logger.info("[INFO] 测试任务已开始！")
    return {"message": "测试开始", "start_time": test_session["start_time"]}


@app.post("/api/test/stop")
def stop_test():
    global test_session
    if not test_session["is_active"]: return {"message": "没有正在进行的测试", "status": "error"}
    test_session["is_active"] = False
    end_time = datetime.datetime.now()
    total = test_session["total_count"]
    abnormal = test_session["abnormal_count"]
    total_latency = test_session["total_latency"]
    pass_rate = ((total - abnormal) / total * 100) if total > 0 else 0
    avg_latency = (total_latency / total) if total > 0 else 0
    conclusion = "通过"
    if pass_rate < 95 or avg_latency > 500: conclusion = "不通过"

    report = {
        "start_time": test_session["start_time"], "end_time": end_time,
        "duration": str(end_time - test_session["start_time"]),
        "total_count": total, "abnormal_count": abnormal,
        "pass_rate": round(pass_rate, 2), "avg_latency": round(avg_latency, 2),
        "conclusion": conclusion
    }
    logger.info(f"[INFO] 测试任务结束！结论: {conclusion}")
    return report


@app.get("/api/test/status")
def get_test_status():
    return {"is_active": test_session["is_active"], "total_count": test_session["total_count"],
            "abnormal_count": test_session["abnormal_count"]}


# --- 配置接口 ---
class ConfigModel(BaseModel):
    temp_min: float
    temp_max: float
    hum_min: float
    hum_max: float
    temp_change_limit: float
    pm25_change_limit: float
    pm25_max: float
    co2_max: float
    lost_timeout: int


@app.get("/api/config")
def get_config():
    return test_config


@app.post("/api/config")
def update_config(config: ConfigModel):
    global test_config
    test_config.update(config.dict())
    logger.info(f"[INFO] 测试规则已更新")
    return {"message": "配置更新成功", "data": test_config}