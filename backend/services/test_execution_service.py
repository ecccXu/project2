"""
测试执行服务
"""
from backend.models import TestResult, Sensor, TestCase
from backend.config.db_config import db
from datetime import datetime
import uuid
import threading
import time
from backend.services.system_service import update_system_status
import re


# 用于存储当前正在执行的测试任务
active_tests = {}


def start_test(test_data):
    """
    开始测试
    """
    sensor_id = test_data.get('sensorId', 'all')
    case_ids = test_data.get('caseIds', [])
    
    # 验证参数
    if not isinstance(case_ids, list) or len(case_ids) == 0:
        raise ValueError("caseIds必须是非空数组")
    
    if sensor_id != 'all':
        # 验证传感器ID格式
        if not re.match(r'^[A-Za-z0-9_-]+$', sensor_id):
            raise ValueError(f"传感器ID格式不正确: {sensor_id}")
        
        sensor = Sensor.query.filter_by(sensor_id=sensor_id).first()
        if not sensor:
            raise ValueError(f"传感器 {sensor_id} 不存在")
    
    # 验证测试用例ID
    for case_id in case_ids:
        case = TestCase.query.filter_by(case_id=case_id).first()
        if not case:
            raise ValueError(f"测试用例 {case_id} 不存在")
        if not case.enabled:
            raise ValueError(f"测试用例 {case_id} 未启用")
    
    # 检查是否已有测试任务在执行
    if active_tests:
        raise ValueError("当前存在正在执行的测试任务，请等待当前任务完成或终止后再启动新任务", 603)
    
    # 生成测试ID
    test_id = f"T-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{str(uuid.uuid4())[:8].upper()}"
    
    # 创建测试任务记录
    active_tests[test_id] = {
        'sensor_id': sensor_id,
        'case_ids': case_ids,
        'start_time': datetime.utcnow(),
        'status': 'running'
    }
    
    # 模拟执行测试（在实际应用中，这里会启动测试引擎）
    # 在后台线程中执行测试
    thread = threading.Thread(target=execute_test_task, args=(test_id, sensor_id, case_ids))
    thread.daemon = True
    thread.start()
    
    return {"testId": test_id}


def execute_test_task(test_id, sensor_id, case_ids):
    """
    执行测试任务（在后台线程中运行）
    """
    try:
        # 确定要测试的传感器列表
        if sensor_id == 'all':
            sensors = Sensor.query.filter_by(status='running').all()
        else:
            sensors = [Sensor.query.filter_by(sensor_id=sensor_id).first()]
        
        # 遍历每个传感器和测试用例进行测试
        for sensor in sensors:
            if sensor:
                for case_id in case_ids:
                    # 模拟测试执行
                    time.sleep(0.1)  # 模拟测试执行时间
                    
                    # 创建测试结果记录
                    case = TestCase.query.filter_by(case_id=case_id).first()
                    if case:
                        # 这里是模拟测试结果，在实际应用中应该通过测试引擎执行
                        # 模拟随机结果（90%通过率）
                        import random
                        result = 'pass' if random.random() < 0.9 else 'fail'
                        
                        details = ""
                        if result == 'pass':
                            if case_id == 'TC-001':  # 温度范围校验
                                details = "温度 25.3℃ 在 [-40, 85] 范围内"
                            elif case_id == 'TC-002':  # 湿度范围校验
                                details = "湿度 48.1% 在 [0, 100] 范围内"
                            elif case_id == 'TC-003':  # 数据格式校验
                                details = "JSON格式正确，字段完整"
                        else:
                            if case_id == 'TC-001':  # 温度范围校验
                                details = "温度 -41.0℃ 小于最小值 -40℃"
                            elif case_id == 'TC-002':  # 湿度范围校验
                                details = "湿度 105% 超出最大值 100%"
                            elif case_id == 'TC-003':  # 数据格式校验
                                details = "JSON格式错误或字段缺失"
                        
                        test_result = TestResult(
                            test_id=test_id,
                            sensor_id=sensor.sensor_id,
                            case_id=case.case_id,
                            case_name=case.name,
                            result=result,
                            details=details,
                            test_time=datetime.utcnow()
                        )
                        db.session.add(test_result)
                        db.session.commit()
        
        # 更新测试任务状态
        if test_id in active_tests:
            active_tests[test_id]['status'] = 'completed'
        
        # 更新系统状态
        update_system_status()
        
    except Exception as e:
        # 记录错误
        if test_id in active_tests:
            active_tests[test_id]['status'] = 'error'
            active_tests[test_id]['error'] = str(e)
    finally:
        # 从活动测试列表中移除
        if test_id in active_tests:
            del active_tests[test_id]


def get_realtime_results(sensor_id=None):
    """
    获取实时测试结果
    """
    query = TestResult.query.order_by(TestResult.test_time.desc())  # 按时间倒序排列
    
    if sensor_id and sensor_id != 'all':
        query = query.filter(TestResult.sensor_id == sensor_id)
    
    # 只返回最近的测试结果
    results = query.limit(50).all()  # 限制返回最近50条记录
    
    result_list = []
    for result in results:
        result_list.append({
            "timestamp": result.test_time.isoformat() if result.test_time else None,
            "sensorId": result.sensor_id,
            "caseId": result.case_id,
            "caseName": result.case_name,
            "result": result.result,
            "details": result.details
        })
    
    return result_list
