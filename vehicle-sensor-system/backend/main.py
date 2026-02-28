# backend/main.py

import asyncio
import json
import threading
import logging
import sys
from fastapi import FastAPI
from paho.mqtt import client as mqtt_client
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware

# 导入数据库模块
from database import SessionLocal, engine, Base
from models import SensorData

# ================= 配置区域 =================
BROKER = 'broker.emqx.io'
PORT = 1883
TOPIC = "vehicle/ESP32_SIM_01/sensors/realtime"
CLIENT_ID = "Backend_Server_01"
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
    try:
        payload = msg.payload.decode()
        data = json.loads(payload)

        # 1. 运行测试引擎
        is_abnormal, error_msg = test_engine(data['data'])

        # 2. 存入数据库
        db: Session = SessionLocal()
        try:
            db_data = SensorData(
                device_id=data['device_id'],
                temperature=data['data']['temperature'],
                humidity=data['data']['humidity'],
                is_abnormal=is_abnormal,
                error_msg=error_msg
            )
            db.add(db_data)
            db.commit()

            # 打印日志，异常数据高亮显示
            status = "🚨 异常" if is_abnormal else "✅ 正常"
            logger.info(f"📥 收到数据: {data['data']['temperature']}℃ | 判定: {status} {error_msg or ''}")

        finally:
            db.close()

    except Exception as e:
        logger.error(f"❌ 处理消息出错: {e}")


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


@app.get("/api/history")
def get_history(limit: int = 20):
    """
    查询最近的历史数据
    """
    db = SessionLocal()
    try:
        # 按时间倒序，取最近的20条
        data = db.query(SensorData).order_by(SensorData.create_time.desc()).limit(limit).all()
        return data
    finally:
        db.close()

@app.get("/api/realtime")
def get_realtime():
    """
    获取最新的一条数据，用于仪表盘展示
    """
    db = SessionLocal()
    try:
        # 查询数据库最新的一条
        data = db.query(SensorData).order_by(SensorData.create_time.desc()).first()
        return data
    finally:
        db.close()