# backend/main.py

import json
import threading
import logging
import sys
import os
import time
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Dict, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from paho.mqtt import client as mqtt_client
from sqlalchemy.orm import Session

# =========================================
# 本地模块导入
# 顺序很重要：database → models → 其他
# =========================================
from database import get_db, init_db, SessionLocal
import models
from models import SensorData, TestReport
from crypto_utils import decrypt_data, encrypt_data
from test_engine import run_content_test, get_default_config

# test_bench 在文件末尾导入，解决循环导入问题
# （test_bench需要本文件的 data_lock 等，但本文件不在顶部导入它）

# ==========================================
# 日志配置
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("MainServer")


# ==========================================
# MQTT 配置
#
# 多节点Topic设计：
#   数据主题: vcar/sensors/+/data
#     + 是MQTT单层通配符，匹配任意node_id
#     例如：vcar/sensors/ENV_SIM_001/data
#           vcar/sensors/ESP32_001/data   ← ESP32接入时自动支持
#
#   控制主题: vcar/sensors/{node_id}/control
#     后端向指定节点下发指令，精确控制
#
# ESP32接入说明（硬件预留接口）：
#   ESP32只需：
#   1. 连接同一Broker
#   2. 使用相同AES密钥
#   3. 发布到 vcar/sensors/ESP32_001/data
#   4. 订阅 vcar/sensors/ESP32_001/control
#   后端无需任何改动即可自动识别新节点
# ==========================================
BROKER      = os.environ.get('MQTT_BROKER', 'localhost')
PORT        = int(os.environ.get('MQTT_PORT', '1883'))
CLIENT_ID   = "Backend_TestBench_V2"
DATA_TOPIC  = "vcar/sensors/+/data"       # 订阅所有节点的数据
CTRL_TOPIC  = "vcar/sensors/+/control"    # 订阅所有节点的控制回显


# ==========================================
# 核心数据层：多节点内存数据池
#
# 数据结构设计：
#
#   node_data_pool = {
#       "ENV_SIM_001": {          ← 模拟器节点
#           "in_car_temp": 25.0,
#           "status": "NORMAL",
#           ...
#       },
#       "ESP32_001": {            ← ESP32硬件节点（接入后自动出现）
#           "in_car_temp": 26.5,
#           ...
#       }
#   }
#
#   node_queue_pool = {
#       "ENV_SIM_001": deque([...], maxlen=100),
#       "ESP32_001":   deque([...], maxlen=100),
#   }
#
#   node_online_time = {
#       "ENV_SIM_001": "2024-01-15 14:30:00",  ← 首次上线时间
#       "ESP32_001":   "2024-01-15 15:00:00",
#   }
# ==========================================
data_lock        = threading.Lock()
node_data_pool   = {}   # {node_id: latest_data_dict}
node_queue_pool  = {}   # {node_id: deque}
node_online_time = {}   # {node_id: 首次上线时间字符串}

DATA_QUEUE_MAX_LEN = 100

# 全局告警阈值配置（可通过API动态修改）
current_test_config = get_default_config()
config_lock = threading.Lock()

# 全局MQTT客户端实例（供test_bench下发指令使用）
mqtt_client_instance = None


# ==========================================
# 工具函数
# ==========================================
def _get_node_id_from_topic(topic: str) -> Optional[str]:
    """
    从MQTT Topic中提取node_id

    例如：
      "vcar/sensors/ENV_SIM_001/data" → "ENV_SIM_001"
      "vcar/sensors/ESP32_001/data"   → "ESP32_001"
    """
    parts = topic.split('/')
    # 格式: vcar / sensors / {node_id} / data
    if len(parts) == 4 and parts[0] == 'vcar' and parts[1] == 'sensors':
        return parts[2]
    return None


def _init_node_pool(node_id: str):
    """
    首次发现新节点时初始化其数据池
    线程安全：调用方需持有 data_lock
    """
    if node_id not in node_data_pool:
        node_data_pool[node_id]   = {}
        node_queue_pool[node_id]  = deque(maxlen=DATA_QUEUE_MAX_LEN)
        node_online_time[node_id] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f"[多节点] 发现新节点: {node_id}，已初始化数据池")


# ==========================================
# 数据库写入（异步，不阻塞MQTT线程）
# ==========================================
def _save_to_db(parsed_item: dict):
    """
    将一条传感器数据异步写入数据库
    在独立线程中执行，不阻塞MQTT消息处理
    """
    db = SessionLocal()
    try:
        record = SensorData(
            sensor_id    = parsed_item.get("sensor_id", "UNKNOWN"),
            in_car_temp  = encrypt_data(str(parsed_item.get("in_car_temp", ""))),
            out_car_temp = encrypt_data(str(parsed_item.get("out_car_temp", ""))),
            humidity     = encrypt_data(str(parsed_item.get("humidity", ""))),
            pm25         = encrypt_data(str(parsed_item.get("pm25", ""))),
            co2          = encrypt_data(str(parsed_item.get("co2", ""))),
            status       = parsed_item.get("status", "NORMAL"),
            fault_code   = parsed_item.get("fault_code", "NONE"),
            latency_ms   = parsed_item.get("latency_ms", 0),
            is_abnormal  = parsed_item.get("is_abnormal", False),
            error_msg    = parsed_item.get("error_msg", None),
            server_time  = datetime.utcnow(),
        )
        db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"[数据库] 写库失败: {e}")
    finally:
        db.close()


# ==========================================
# MQTT 回调函数
# ==========================================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logger.info(f"[MQTT] 成功连接到 Broker: {BROKER}:{PORT}")
        client.subscribe(DATA_TOPIC, qos=1)
        logger.info(f"[MQTT] 已订阅多节点数据主题: {DATA_TOPIC}")
    else:
        logger.error(f"[MQTT] 连接失败，错误码: {rc}")


def on_message(client, userdata, msg):
    """
    MQTT消息处理：解密 → 解析 → 合规校验 → 更新内存池 → 异步写库

    职责边界：
      本函数只负责数据采集和分发
      业务判定由 test_engine.run_content_test() 负责
      数据库写入在独立线程中异步执行
    """
    # 忽略控制主题的消息
    if '/control' in msg.topic:
        return

    # 1. 从Topic提取node_id
    node_id = _get_node_id_from_topic(msg.topic)
    if not node_id:
        logger.warning(f"[MQTT] 无法解析节点ID，Topic: {msg.topic}")
        return

    try:
        # 2. AES-CBC解密
        encrypted_payload = msg.payload.decode('utf-8')
        decrypted_json    = decrypt_data(encrypted_payload)
        if decrypted_json is None:
            logger.error(f"[{node_id}] 解密失败，丢弃数据包（可能被篡改）")
            return

        # 3. JSON解析
        data        = json.loads(decrypted_json)
        sensor_data = data.get('data', {})

        # 4. 计算传输延迟
        send_time  = data.get('send_time')
        latency_ms = int(time.time() * 1000 - send_time) if send_time else None

        # 5. 构建标准化数据项
        parsed_item = {
            "sensor_id":   node_id,
            "timestamp":   data.get('timestamp'),
            "in_car_temp": sensor_data.get('in_car_temp', 0.0),
            "out_car_temp":sensor_data.get('out_car_temp', 0.0),
            "humidity":    sensor_data.get('humidity', 0.0),
            "pm25":        sensor_data.get('pm25', 0.0),
            "co2":         sensor_data.get('co2', 0.0),
            "status":      data.get('status', 'NORMAL'),
            "fault_code":  data.get('fault_code', 'NONE'),
            "latency_ms":  latency_ms,
        }

        # 6. 第一层测试：合规性校验
        with config_lock:
            cfg = current_test_config.copy()
        is_abnormal, error_msg = run_content_test(parsed_item, config=cfg)
        parsed_item["is_abnormal"] = is_abnormal
        parsed_item["error_msg"]   = error_msg

        if is_abnormal:
            logger.warning(f"[{node_id}] 数据异常告警: {error_msg}")

        # 7. 线程安全地更新多节点内存数据池
        with data_lock:
            _init_node_pool(node_id)
            node_data_pool[node_id].update(parsed_item)
            node_queue_pool[node_id].append(parsed_item)

        # 8. 异步写库（独立线程，不阻塞消息处理）
        threading.Thread(
            target=_save_to_db,
            args=(parsed_item,),
            daemon=True
        ).start()

    except json.JSONDecodeError:
        logger.error(f"[{node_id}] JSON解析失败")
    except Exception as e:
        logger.error(f"[{node_id}] 消息处理异常: {e}")


def mqtt_thread_task():
    """MQTT后台线程：连接Broker并保持消息循环"""
    global mqtt_client_instance
    client = mqtt_client.Client(CLIENT_ID)
    mqtt_client_instance = client
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(BROKER, PORT, keepalive=60)
        client.loop_forever()
    except Exception as e:
        logger.error(f"[MQTT] 线程异常退出: {e}")


# ==========================================
# FastAPI 应用初始化
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    from test_bench import executor as _executor

    # ✅ 注入三个依赖函数
    def _data_provider(node_id: str) -> dict:
        with data_lock:
            return node_data_pool.get(node_id, {}).copy()

    def _queue_provider(node_id: str, count: int) -> list:
        with data_lock:
            q = node_queue_pool.get(node_id, deque())
            lst = list(q)
            return lst[-count:] if len(lst) >= count else lst

    def _mqtt_publisher(node_id: str, command: str, params: dict) -> bool:
        if not mqtt_client_instance:
            return False
        topic   = f"vcar/sensors/{node_id}/control"
        payload = json.dumps({"command": command, "params": params})
        mqtt_client_instance.publish(topic, payload, qos=1)
        return True

    _executor.inject_dependencies(
        data_provider  = _data_provider,
        queue_provider = _queue_provider,
        mqtt_publisher = _mqtt_publisher,
    )

    app.state.executor = _executor
    logger.info("[系统启动] 测试引擎依赖注入完成")

    thread = threading.Thread(target=mqtt_thread_task, daemon=True)
    thread.start()
    logger.info("[系统启动] 全部初始化完成")
    yield

    logger.info("[系统关闭] 正在清理资源...")
    if mqtt_client_instance:
        mqtt_client_instance.disconnect()


app = FastAPI(
    title="车载环境传感器测试系统",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# API路由：节点管理
# ==========================================
@app.get("/api/nodes", summary="获取所有在线节点列表")
def get_nodes():
    """
    返回当前所有已上线的节点信息
    ESP32接入后会自动出现在列表中，无需任何后端改动
    """
    with data_lock:
        nodes = []
        for node_id, online_time in node_online_time.items():
            latest = node_data_pool.get(node_id, {})
            nodes.append({
                "node_id":     node_id,
                "online_time": online_time,
                "status":      latest.get("status", "UNKNOWN"),
                "is_abnormal": latest.get("is_abnormal", False),
                "last_update": latest.get("timestamp"),
            })
    return {"nodes": nodes, "total": len(nodes)}


@app.get("/api/nodes/{node_id}", summary="获取指定节点的最新数据")
def get_node_detail(node_id: str):
    """获取指定节点的最新传感器数据（明文，供前端实时显示）"""
    with data_lock:
        if node_id not in node_data_pool:
            raise HTTPException(
                status_code=404,
                detail=f"节点 '{node_id}' 不存在或尚未上线"
            )
        latest = node_data_pool[node_id].copy()
        queue  = list(node_queue_pool[node_id])

    return {
        "node_id":     node_id,
        "online_time": node_online_time.get(node_id),
        "latest_data": latest,
        "queue_length":len(queue),
    }


# ==========================================
# API路由：实时数据
# ==========================================
@app.get("/api/debug/pool", summary="查看所有节点内存数据池状态")
def get_pool_status():
    """调试接口：查看多节点内存数据池（兼容旧版前端）"""
    with data_lock:
        result = {}
        for node_id in node_data_pool:
            queue = node_queue_pool[node_id]
            result[node_id] = {
                "latest_data_snapshot": node_data_pool[node_id].copy(),
                "queue_length":         len(queue),
            }
    return result


@app.get("/api/debug/pool/{node_id}", summary="查看指定节点内存数据池")
def get_node_pool_status(node_id: str):
    """查看指定节点的内存数据池状态"""
    with data_lock:
        if node_id not in node_data_pool:
            raise HTTPException(status_code=404, detail=f"节点 '{node_id}' 不存在")
        snapshot = node_data_pool[node_id].copy()
        queue    = list(node_queue_pool[node_id])
        latest   = queue[-1] if queue else None
    return {
        "node_id":              node_id,
        "queue_length":         len(queue),
        "max_queue_length":     DATA_QUEUE_MAX_LEN,
        "latest_data_snapshot": snapshot,
        "latest_in_queue":      latest,
    }

def _safe_decrypt_float(encrypted_str: Optional[str]) -> Optional[float]:
    """安全解密数值字段，失败返回None"""
    if not encrypted_str:
        return None
    try:
        decrypted = decrypt_data(encrypted_str)
        return float(decrypted) if decrypted else None
    except (ValueError, TypeError):
        return None
# ==========================================
# API路由：历史数据查询
# ==========================================
@app.get("/api/data/history", summary="历史传感器数据查询")
def get_history(
    node_id:     Optional[str] = Query(None,  description="节点ID筛选，为空则查全部"),
    is_abnormal: Optional[bool] = Query(None, description="是否只看异常数据"),
    limit:       int            = Query(50,   description="每页条数", ge=1, le=200),
    offset:      int            = Query(0,    description="偏移量（分页用）", ge=0),
    db:          Session        = Depends(get_db)
):
    """
    查询历史传感器数据
    数值字段返回解密后的明文，方便前端直接展示
    """
    query = db.query(SensorData)

    # 筛选条件
    if node_id:
        query = query.filter(SensorData.sensor_id == node_id)
    if is_abnormal is not None:
        query = query.filter(SensorData.is_abnormal == is_abnormal)

    total   = query.count()
    records = (
        query
        .order_by(SensorData.server_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # 解密数值字段后返回
    result = []
    for r in records:
        item = r.to_dict()
        # 解密数值字段（解密失败时返回None）
        item["in_car_temp"]  = _safe_decrypt_float(r.in_car_temp)
        item["out_car_temp"] = _safe_decrypt_float(r.out_car_temp)
        item["humidity"]     = _safe_decrypt_float(r.humidity)
        item["pm25"]         = _safe_decrypt_float(r.pm25)
        item["co2"]          = _safe_decrypt_float(r.co2)
        result.append(item)

    return {
        "total":  total,
        "offset": offset,
        "limit":  limit,
        "data":   result,
    }


# ==========================================
# API路由：告警阈值配置
# ==========================================
@app.get("/api/config/thresholds", summary="获取当前告警阈值")
def get_thresholds():
    """获取当前生效的告警阈值配置"""
    with config_lock:
        return {"config": current_test_config.copy()}


@app.put("/api/config/thresholds", summary="更新告警阈值")
def update_thresholds(new_config: Dict[str, float]):
    """
    动态更新告警阈值，立即生效，无需重启
    只更新传入的字段，未传入的字段保持不变
    """
    global current_test_config
    with config_lock:
        current_test_config.update(new_config)
        updated = current_test_config.copy()
    logger.info(f"[配置] 告警阈值已更新: {new_config}")
    return {"message": "阈值更新成功", "config": updated}


# ==========================================
# API路由：台架测试
# ==========================================
@app.post("/api/bench/run", summary="启动台架测试")
def run_bench(
    req:     List[Dict],
    node_id: str = Query("ENV_SIM_001", description="指定测试目标节点")
):
    """
    启动台架自动化测试
    req格式：[{"id": "case_temp_step", "params": {"target_temp": 80}}]
    node_id：指定本次测试针对哪个节点（默认模拟器节点）
    """
    executor = app.state.executor
    if not req:
        raise HTTPException(status_code=400, detail="用例列表为空")

    success = executor.start(config=req, node_id=node_id)
    if success:
        return {
            "message": f"已启动 {len(req)} 个用例，目标节点: {node_id}",
            "status":  "success"
        }
    return {
        "message": "台架正在运行中，请勿重复提交",
        "status":  "error"
    }


@app.post("/api/bench/stop", summary="强制停止台架测试")
def stop_bench():
    """强制停止正在运行的测试，当前用例执行完毕后停止"""
    executor = app.state.executor
    if not executor.is_running:
        return {"message": "台架当前未在运行", "status": "idle"}
    executor.stop()
    return {"message": "已发送停止信号，当前用例执行完毕后停止", "status": "stopping"}


@app.get("/api/bench/cases", summary="获取所有可用测试用例")
def get_available_cases():
    """获取注册中心中所有可用的测试用例及其默认参数"""
    executor = app.state.executor
    safe_metadata = [
        {
            "id":             case_id,
            "name":           meta["name"],
            "type":           meta["type"],
            "default_params": meta["default_params"],
        }
        for case_id, meta in executor.registry.items()
    ]
    return {"cases": safe_metadata}


@app.get("/api/bench/status", summary="获取台架运行状态")
def get_bench_status():
    """获取台架当前运行状态、进度和结果摘要"""
    executor = app.state.executor
    return {
        "is_running":       executor.is_running,
        "current_case":     executor.current_case_name,
        "target_node":      getattr(executor, 'target_node_id', 'N/A'),
        "progress":         f"{executor.progress}/{executor.total_cases}",
        "results_summary":  [
            {"case_id": r.get("case_id"), "case": r["case"], "status": r["status"]}
            for r in executor.results
        ],
    }


@app.get("/api/bench/logs", summary="获取台架执行日志")
def get_bench_logs():
    """获取最近50条台架执行日志"""
    executor = app.state.executor
    logs = list(executor.logs)
    return {"logs": logs[-50:]}


@app.get("/api/bench/report", summary="获取本次测试报告")
def get_bench_report():
    """获取本次测试的完整报告（测试结束后可用）"""
    executor = app.state.executor
    if executor.is_running:
        raise HTTPException(status_code=400, detail="测试尚未结束")
    if not executor.results:
        raise HTTPException(status_code=404, detail="暂无测试结果")

    pass_count  = sum(1 for r in executor.results if r["status"] == "PASS")
    fail_count  = sum(1 for r in executor.results if r["status"] == "FAIL")
    error_count = sum(1 for r in executor.results if r["status"] == "ERROR")
    total       = len(executor.results)

    return {
        "status":      "success",
        "target_node": getattr(executor, 'target_node_id', 'N/A'),
        "total":       total,
        "pass_count":  pass_count,
        "fail_count":  fail_count,
        "error_count": error_count,
        "pass_rate":   round(pass_count / total * 100, 1) if total > 0 else 0,
        "details":     executor.results,
    }

@app.post("/api/bench/cases/custom", summary="新增自定义用例")
def add_custom_case(case_data: dict):
    """新增一个自定义测试用例"""
    executor = app.state.executor
    result = executor.add_custom_case(case_data)
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=400, detail=result["message"])

@app.delete("/api/bench/cases/custom/{case_id}", summary="删除自定义用例")
def remove_custom_case(case_id: str):
    """删除一个自定义测试用例"""
    executor = app.state.executor
    result = executor.remove_custom_case(case_id)
    if result["success"]:
        return result
    else:
        raise HTTPException(status_code=400, detail=result["message"])
# ==========================================
# API路由：测试报告持久化
# ==========================================
@app.post("/api/reports/save", summary="保存测试报告到数据库")
def save_report(db: Session = Depends(get_db)):
    """
    将本次测试结果保存到数据库
    建议在前端确认报告后调用
    """
    executor = app.state.executor
    if executor.is_running:
        raise HTTPException(status_code=400, detail="测试尚未结束，无法保存")
    if not executor.results:
        raise HTTPException(status_code=404, detail="暂无测试结果可保存")

    results     = executor.results
    total       = len(results)
    pass_count  = sum(1 for r in results if r["status"] == "PASS")
    fail_count  = sum(1 for r in results if r["status"] == "FAIL")
    error_count = sum(1 for r in results if r["status"] == "ERROR")
    node_id     = getattr(executor, 'target_node_id', 'UNKNOWN')

    report = TestReport(
        report_name = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} [{node_id}] 测试报告",
        node_id     = node_id,
        total_cases = total,
        pass_count  = pass_count,
        fail_count  = fail_count,
        error_count = error_count,
        pass_rate   = pass_count / total if total > 0 else 0.0,
        details     = json.dumps(results, ensure_ascii=False),
        create_time = datetime.utcnow(),
    )

    db.add(report)
    db.commit()
    db.refresh(report)

    logger.info(f"[报告] 已保存测试报告 id={report.id}，节点={node_id}")
    return {
        "message":   "报告保存成功",
        "report_id": report.id,
        "report":    report.to_dict(),
    }


@app.get("/api/reports/list", summary="获取历史测试报告列表")
def get_reports_list(
    node_id: Optional[str] = Query(None, description="按节点筛选"),
    limit:   int           = Query(20,   description="每页条数", ge=1, le=100),
    offset:  int           = Query(0,    description="偏移量", ge=0),
    db:      Session       = Depends(get_db)
):
    """获取历史测试报告列表（分页）"""
    query = db.query(TestReport)
    if node_id:
        query = query.filter(TestReport.node_id == node_id)

    total   = query.count()
    reports = (
        query
        .order_by(TestReport.create_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "total":   total,
        "offset":  offset,
        "limit":   limit,
        "reports": [r.to_dict() for r in reports],
    }


@app.get("/api/reports/{report_id}", summary="获取指定报告详情")
def get_report_detail(report_id: int, db: Session = Depends(get_db)):
    """获取指定报告的完整详情，包含每个用例的结果"""
    report = db.query(TestReport).filter(TestReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"报告 id={report_id} 不存在")
    return {"report": report.to_detail_dict()}


# ==========================================
# 根路由
# ==========================================
@app.get("/", summary="服务状态")
def read_root():
    return {
        "message": "车载环境传感器测试系统 v2.0",
        "status":  "running",
        "docs":    "/docs",    # FastAPI自动生成的API文档
    }
