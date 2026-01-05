"""
数据查询服务
"""
from backend.models import TestResult, SensorData
from backend.config.db_config import db
from backend.utils.response import paginate_response
from datetime import datetime


def query_test_results(sensor_id=None, start_time=None, end_time=None, page=1, page_size=10):
    """
    查询历史测试结果
    """
    query = TestResult.query
    
    # 根据传感器ID过滤
    if sensor_id:
        query = query.filter(TestResult.sensor_id == sensor_id)
    
    # 根据时间范围过滤
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            query = query.filter(TestResult.test_time >= start_dt)
        except ValueError:
            raise ValueError(f"开始时间格式不正确: {start_time}")
    
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            query = query.filter(TestResult.test_time <= end_dt)
        except ValueError:
            raise ValueError(f"结束时间格式不正确: {end_time}")
    
    # 按时间倒序排列
    query = query.order_by(TestResult.test_time.desc())
    
    # 分页处理
    def format_test_result_item(item):
        return {
            "testId": item.test_id,
            "sensorId": item.sensor_id,
            "caseId": item.case_id,
            "caseName": item.case_name,
            "result": item.result,
            "testTime": item.test_time.isoformat() if item.test_time else None,
            "details": item.details
        }
    
    return paginate_response(query, page, page_size, format_test_result_item)


def query_sensor_data(sensor_id=None, source=None, start_time=None, end_time=None, page=1, page_size=10):
    """
    查询原始传感器数据
    """
    query = SensorData.query
    
    # 根据传感器ID过滤
    if sensor_id:
        query = query.filter(SensorData.sensor_id == sensor_id)
    
    # 根据数据来源过滤
    if source:
        if source not in ['simulation', 'real']:
            raise ValueError(f"数据来源参数不正确: {source}，应为 'simulation' 或 'real'")
        query = query.filter(SensorData.source == source)
    
    # 根据时间范围过滤
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            query = query.filter(SensorData.receive_time >= start_dt)
        except ValueError:
            raise ValueError(f"开始时间格式不正确: {start_time}")
    
    if end_time:
        try:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            query = query.filter(SensorData.receive_time <= end_dt)
        except ValueError:
            raise ValueError(f"结束时间格式不正确: {end_time}")
    
    # 按时间倒序排列
    query = query.order_by(SensorData.receive_time.desc())
    
    # 分页处理
    def format_sensor_data_item(item):
        return {
            "dataId": item.data_id,
            "sensorId": item.sensor_id,
            "temperature": item.temperature,
            "humidity": item.humidity,
            "receiveTime": item.receive_time.isoformat() if item.receive_time else None,
            "source": item.source
        }
    
    return paginate_response(query, page, page_size, format_sensor_data_item)