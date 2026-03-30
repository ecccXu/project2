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
from test_engine import run_content_test

# 引入解密工具
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crypto_utils import decrypt_data, encrypt_data

# 导入数据库模块
from database import SessionLocal, engine, Base
from models import SensorData
from pydantic import BaseModel

# ================= 配置区域 =================
BROKER = 'broker.emqx.io'
PORT = 1883
TOPIC = "vehicle/ESP32_SIM_01/sensors/realtime"
CLIENT_ID = "Backend_Server_01"
# --- 全局状态：用于丢包检测 ---
# 结构: { "设备ID": 上一次收到的时间戳 }
device_last_timestamp = {}
# --- 全局状态：用于测试任务管理 ---
test_session = {
    "is_active": False,       # 测试是否正在进行
    "start_time": None,       # 测试开始时间
    "total_count": 0,         # 本次测试总条数
    "abnormal_count": 0,      # 本次异常条数
    "total_latency": 0,       # 本次测试总延迟 (秒)
}
# --- 全局状态：用于突变检测 ---
device_last_values = {}
# --- 全局状态：动态测试规则配置 ---
test_config = {
    "temp_min": -40.0,       # 温度下限
    "temp_max": 85.0,        # 温度上限
    "hum_min": 0.0,          # 湿度下限
    "hum_max": 100.0,        # 湿度上限
    "temp_change_limit": 5.0, # 温度突变阈值 (℃)
    "hum_change_limit": 10.0, # 湿度突变阈值 (%)
    "lost_timeout": 5         # 丢包判定超时 (秒)
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
# 启动时自动创建表文件
Base.metadata.create_all(bind=engine)
logger.info("[INFO] 数据库表结构检查完成")

app = FastAPI()
# --- 配置跨域 ---
origins = ["*"] # 允许所有来源，开发阶段方便
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
        logger.info("[INFO] <Backend> 成功连接到 MQTT Broker")
        client.subscribe(TOPIC)
    else:
        logger.error(f"[ERROR] <Backend> 连接失败，代码: {rc}")


def on_message(client, userdata, msg):
    """
    核心回调函数：
    解密 -> 连续性检测(丢包) -> 稳定性检测(突变) -> 内容校验(范围) -> 加密存储
    """
    global device_last_timestamp, device_last_values, test_session, test_config

    try:
        # ================= 1. 安全模块：解密 =================
        encrypted_payload = msg.payload.decode()
        decrypted_json = decrypt_data(encrypted_payload)

        if decrypted_json is None:
            logger.error("[ERROR] <Security> 解密失败！数据可能被篡改。")
            return

        data = json.loads(decrypted_json)

        # 提取核心数据
        current_device_id = data['device_id']
        current_timestamp = data['timestamp']
        current_temp = data['data']['temperature']
        current_hum = data['data']['humidity']

        # ================= 2. 通信连续性检测 (丢包) =================
        continuity_errors = []
        if current_device_id in device_last_timestamp:
            last_ts = device_last_timestamp[current_device_id]
            diff = current_timestamp - last_ts

            # 使用动态配置的阈值
            if diff > test_config["lost_timeout"]:
                continuity_errors.append(f"通信不连续: 间隔{diff}秒")

        # 更新最后时间戳
        device_last_timestamp[current_device_id] = current_timestamp

        # ================= 3. 数据稳定性检测 (突变) =================
        stability_errors = []
        # 使用动态配置的阈值
        temp_change_limit = test_config["temp_change_limit"]
        hum_change_limit = test_config["hum_change_limit"]

        if current_device_id in device_last_values:
            last_temp = device_last_values[current_device_id]['temperature']
            last_hum = device_last_values[current_device_id]['humidity']

            # 计算差值
            temp_diff = abs(current_temp - last_temp)
            hum_diff = abs(current_hum - last_hum)

            if temp_diff > temp_change_limit:
                stability_errors.append(f"温度突变: {last_temp}℃ -> {current_temp}℃")
            if hum_diff > hum_change_limit:
                stability_errors.append(f"湿度突变: {last_hum}% -> {current_hum}%")

        # 更新最后一次的数值记录
        device_last_values[current_device_id] = {
            'temperature': current_temp,
            'humidity': current_hum
        }

        # ================= 4. 自动化测试引擎 (内容校验) =================
        # 调用修改后的 run_content_test，它会自动读取 test_config
        is_abnormal_content, error_msg_content = run_content_test(data['data'], test_config)

        # ================= 5. 合并所有的错误信息 =================
        all_errors = continuity_errors + stability_errors
        if error_msg_content:
            all_errors.append(error_msg_content)

        final_is_abnormal = len(all_errors) > 0
        final_error_msg = "; ".join(all_errors)

        # ================= 6. 计算延迟 =================
        # 提取发送时间，如果不存在则默认为当前时间(延迟为0)
        send_time = data.get('send_time', 0)
        current_time_ms = time.time() * 1000
        latency_ms = int(current_time_ms - send_time) if send_time else 0

        # ================= 7. 测试任务管理与入库 =================
        if test_session["is_active"]:
            # 更新全局统计
            test_session["total_count"] += 1
            if final_is_abnormal:
                test_session["abnormal_count"] += 1

            # 【修复】累加延迟用于计算平均值
            test_session["total_latency"] += latency_ms

            # 数据库操作
            db = SessionLocal()
            try:
                # 【存储加密】将数值转为字符串后加密
                encrypted_temp = encrypt_data(str(current_temp))
                encrypted_hum = encrypt_data(str(current_hum))

                db_data = SensorData(
                    device_id=current_device_id,
                    temperature=encrypted_temp,
                    humidity=encrypted_hum,
                    latency=latency_ms,  # 使用定义好的变量
                    is_abnormal=final_is_abnormal,
                    error_msg=final_error_msg
                )
                db.add(db_data)
                db.commit()

                # 打印日志
                status = "x 异常" if final_is_abnormal else "v 正常"
                logger.info(
                    f"[INFO] <测试中> 温度: {current_temp}℃ | 延迟: {latency_ms}ms | 判定: {status} {final_error_msg or ''}")

            except Exception as db_err:
                logger.error(f"[ERROR] 数据库写入错误: {db_err}")
            finally:
                db.close()
        else:
            # 测试未开启，仅打印日志不入库
            logger.info(f"[INFO] <待机> 忽略数据: {current_temp}℃")

    except json.JSONDecodeError:
        logger.error("[ERROR] 数据解析失败：非JSON格式")
    except KeyError as e:
        logger.error(f"[ERROR] 数据字段缺失: {e}")
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


# --- FastAPI 生命周期 ---
@app.on_event("startup")
def startup_event():
    logger.info("[INFO] 后端服务启动，正在启动 MQTT 监听线程...")
    thread = threading.Thread(target=mqtt_thread_task, daemon=True)
    thread.start()


# --- API 接口 ---
@app.get("/")
def read_root():
    return {"message": "系统运行中，数据库已连接"}


@app.get("/api/realtime")
def get_realtime():
    """
    获取最新的一条数据 (需解密后返回)
    """
    db = SessionLocal()
    try:
        # 查询最新的一条
        data = db.query(SensorData).order_by(SensorData.create_time.desc()).first()

        if data is None:
            return None

        # 【新增】解密数据
        # 如果数据库里是密文，解密后转回浮点数
        # 如果解密失败（比如是旧数据），则尝试直接转换
        try:
            temp_val = float(decrypt_data(data.temperature))
            hum_val = float(decrypt_data(data.humidity))
        except:
            temp_val = 0.0
            hum_val = 0.0

        # 返回明文给前端
        return {
            "id": data.id,
            "device_id": data.device_id,
            "temperature": temp_val,
            "humidity": hum_val,
            "latency": data.latency,
            "is_abnormal": data.is_abnormal,
            "error_msg": data.error_msg,
            "create_time": data.create_time
        }
    finally:
        db.close()


@app.get("/api/history")
def get_history(limit: int = 20):
    """
    查询最近的历史数据 (需解密后返回)
    """
    db = SessionLocal()
    try:
        data_list = db.query(SensorData).order_by(SensorData.create_time.desc()).limit(limit).all()

        result = []
        for item in data_list:
            # 解密数据
            # 如果数据库里是密文，解密后转回浮点数
            # 如果解密失败（比如是旧数据），则尝试直接转换
            try:
                temp_val = float(decrypt_data(item.temperature))
                hum_val = float(decrypt_data(item.humidity))
            except:
                temp_val = 0.0
                hum_val = 0.0

            result.append({
                "id": item.id,
                "device_id": item.device_id,
                "temperature": temp_val,
                "humidity": hum_val,
                "latency": item.latency,
                "is_abnormal": item.is_abnormal,
                "error_msg": item.error_msg,
                "create_time": item.create_time
            })
        return result
    finally:
        db.close()


# --- 测试任务管理接口 ---

@app.post("/api/test/start")
def start_test():
    """
    开始测试任务
    """
    if test_session["is_active"]:
        return {"message": "测试已在进行中", "status": "error"}

    test_session["is_active"] = True
    test_session["start_time"] = datetime.datetime.now()
    test_session["total_count"] = 0
    test_session["abnormal_count"] = 0

    logger.info("[INFO] 测试任务已开始！")
    return {"message": "测试开始", "start_time": test_session["start_time"]}


@app.post("/api/test/stop")
def stop_test():
    """
    结束测试任务并生成详细报告
    """
    global test_session
    if not test_session["is_active"]:
        return {"message": "没有正在进行的测试", "status": "error"}

    test_session["is_active"] = False
    end_time = datetime.datetime.now()

    total = test_session["total_count"]
    abnormal = test_session["abnormal_count"]
    total_latency = test_session["total_latency"]

    # 1. 计算通过率
    pass_rate = ((total - abnormal) / total * 100) if total > 0 else 0

    # 2. 计算平均延迟
    avg_latency = (total_latency / total) if total > 0 else 0

    # 3. 生成综合结论 (示例)
    conclusion = "通过"
    if pass_rate < 95:
        conclusion = "不通过"
    elif avg_latency > 500:
        conclusion = "不通过"

    report = {
        "start_time": test_session["start_time"],
        "end_time": end_time,
        "duration": str(end_time - test_session["start_time"]),
        "total_count": total,
        "abnormal_count": abnormal,
        "pass_rate": round(pass_rate, 2),
        "avg_latency": round(avg_latency, 2),
        "conclusion": conclusion
    }

    # 重置计数器 (保留配置)
    test_session["total_count"] = 0
    test_session["abnormal_count"] = 0
    test_session["total_latency"] = 0

    logger.info(f"[INFO] 测试任务结束！结论: {conclusion}")
    return report


@app.get("/api/test/status")
def get_test_status():
    """
    获取当前测试状态
    """
    return {
        "is_active": test_session["is_active"],
        "total_count": test_session["total_count"],
        "abnormal_count": test_session["abnormal_count"]
    }

# 定义请求数据模型
class ConfigModel(BaseModel):
    temp_min: float
    temp_max: float
    hum_min: float
    hum_max: float
    temp_change_limit: float
    hum_change_limit: float
    lost_timeout: int


@app.get("/api/config")
def get_config():
    """获取当前测试配置"""
    return test_config


@app.post("/api/config")
def update_config(config: ConfigModel):
    """更新测试配置"""
    global test_config
    # 更新字典值
    test_config["temp_min"] = config.temp_min
    test_config["temp_max"] = config.temp_max
    test_config["hum_min"] = config.hum_min
    test_config["hum_max"] = config.hum_max
    test_config["temp_change_limit"] = config.temp_change_limit
    test_config["hum_change_limit"] = config.hum_change_limit
    test_config["lost_timeout"] = config.lost_timeout

    logger.info(f"[INFO] 测试规则已更新: 温度范围[{config.temp_min}, {config.temp_max}]")
    return {"message": "配置更新成功", "data": test_config}