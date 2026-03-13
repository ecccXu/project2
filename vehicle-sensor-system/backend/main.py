# backend/main.py

import asyncio
import datetime
import json
import threading
import logging
import sys
import os
from fastapi import FastAPI
from paho.mqtt import client as mqtt_client
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

# 引入解密工具
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from crypto_utils import decrypt_data, encrypt_data

# 导入数据库模块
from database import SessionLocal, engine, Base
from models import SensorData

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
logger.info("✅ 数据库表结构检查完成")

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

# --- 核心功能：自动化测试引擎 ---
def test_engine(data: dict):
    """
    对传感器数据进行多维度校验
    返回: (是否异常, 错误信息)
    """
    errors = []
    temp = data.get('temperature', 0)
    hum = data.get('humidity', 0)

    # 1. 温度范围测试 (模拟车载工况：-40 到 85 度)
    if temp < -40 or temp > 85:
        errors.append(f"温度超限: {temp}℃")

    # 2. 湿度范围测试 (0% - 100%)
    if hum < 0 or hum > 100:
        errors.append(f"湿度非法: {hum}%")

    # 3. 简单的逻辑测试 (例如：温度>80且湿度<5%，可能意味着传感器故障)
    if temp > 80 and hum < 5:
        errors.append("疑似传感器故障：高温低湿")

    is_abnormal = len(errors) > 0
    error_msg = "; ".join(errors) if errors else None

    return is_abnormal, error_msg


# --- MQTT 消息处理 ---
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info("✅ [后端] 成功连接到 MQTT Broker")
        client.subscribe(TOPIC)
    else:
        logger.error(f"❌ [后端] 连接失败，代码: {rc}")


def on_message(client, userdata, msg):
    """
    核心回调函数：解密 -> 连续性检测 -> 内容校验 -> 任务状态判断 -> 加密存储
    """
    global device_last_timestamp, test_session

    try:
        # ================= 1. 安全模块：解密 =================
        encrypted_payload = msg.payload.decode()
        decrypted_json = decrypt_data(encrypted_payload)

        if decrypted_json is None:
            logger.error("❌ [安全模块] 解密失败！数据可能被篡改。")
            return

        data = json.loads(decrypted_json)

        # ================= 2. 通信连续性检测 (丢包率) =================
        current_device_id = data['device_id']
        current_timestamp = data['timestamp']

        continuity_errors = []

        if current_device_id in device_last_timestamp:
            last_ts = device_last_timestamp[current_device_id]
            diff = current_timestamp - last_ts

            # 阈值设定：正常2秒，超过5秒判定为丢包
            if diff > 5:
                continuity_errors.append(f"通信不连续: 间隔{diff}秒")

        # 更新最后时间戳
        device_last_timestamp[current_device_id] = current_timestamp

        # ================= 3. 自动化测试引擎 (内容校验) =================
        is_abnormal_content, error_msg_content = test_engine(data['data'])

        # 合并所有错误信息
        all_errors = continuity_errors
        if error_msg_content:
            all_errors.append(error_msg_content)

        final_is_abnormal = len(all_errors) > 0
        final_error_msg = "; ".join(all_errors)

        # ================= 4. 测试任务管理与入库 =================
        # 只有当测试任务开启时，才进行入库统计
        if test_session["is_active"]:
            # 更新全局统计
            test_session["total_count"] += 1
            if final_is_abnormal:
                test_session["abnormal_count"] += 1

            # 数据库操作
            db = SessionLocal()
            try:
                # 【存储加密】将数值转为字符串后加密
                plain_temp = str(data['data']['temperature'])
                plain_hum = str(data['data']['humidity'])

                encrypted_temp = encrypt_data(plain_temp)
                encrypted_hum = encrypt_data(plain_hum)

                db_data = SensorData(
                    device_id=current_device_id,
                    temperature=encrypted_temp,
                    humidity=encrypted_hum,
                    is_abnormal=final_is_abnormal,
                    error_msg=final_error_msg
                )
                db.add(db_data)
                db.commit()

                # 打印日志
                status = "🚨 异常" if final_is_abnormal else "✅ 正常"
                logger.info(f"📥 [测试中] 温度: {plain_temp}℃ | 判定: {status} {final_error_msg or ''}")

            except Exception as db_err:
                logger.error(f"❌ 数据库写入错误: {db_err}")
            finally:
                db.close()
        else:
            # 测试未开启，仅打印日志不入库
            logger.info(f"⏸️ [待机] 忽略数据: {data['data']['temperature']}℃")

    except json.JSONDecodeError:
        logger.error("❌ 数据解析失败：非JSON格式")
    except KeyError as e:
        logger.error(f"❌ 数据字段缺失: {e}")
    except Exception as e:
        logger.error(f"❌ 处理消息时发生未知错误: {e}")

def mqtt_thread_task():
    client = mqtt_client.Client(CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_forever()
    except Exception as e:
        logger.error(f"MQTT 线程异常: {e}")


# --- FastAPI 生命周期 ---
@app.on_event("startup")
def startup_event():
    logger.info("🚀 后端服务启动，正在启动 MQTT 监听线程...")
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
            # 【新增】解密每一条数据
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

    logger.info("🚀 测试任务已开始！")
    return {"message": "测试开始", "start_time": test_session["start_time"]}


@app.post("/api/test/stop")
def stop_test():
    """
    结束测试任务并生成报告
    """
    if not test_session["is_active"]:
        return {"message": "没有正在进行的测试", "status": "error"}

    test_session["is_active"] = False
    end_time = datetime.datetime.now()

    # 计算通过率
    total = test_session["total_count"]
    abnormal = test_session["abnormal_count"]
    pass_rate = ((total - abnormal) / total * 100) if total > 0 else 0

    report = {
        "start_time": test_session["start_time"],
        "end_time": end_time,
        "total_count": total,
        "abnormal_count": abnormal,
        "pass_rate": round(pass_rate, 2)
    }

    logger.info(f"🛑 测试任务结束！通过率: {pass_rate}%")
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