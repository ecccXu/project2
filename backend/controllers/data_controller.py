"""
数据查询控制器
"""
from flask import Blueprint, request, send_file, make_response
from utils.response import success_response, error_response
from services.data_service import query_test_results, query_sensor_data
from datetime import datetime
import os
from werkzeug.utils import secure_filename

# 创建蓝图
data_bp = Blueprint('data', __name__, url_prefix='/api/v1')

@data_bp.route('/data/test-results', methods=['GET'])
def get_test_results():
    """
    查询历史测试结果
    """
    try:
        # 获取查询参数
        sensor_id = request.args.get('sensorId')
        start_time = request.args.get('startTime')
        end_time = request.args.get('endTime')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 10))
        
        # 验证参数
        if page_size > 100:
            page_size = 100  # 限制最大页面大小
        
        results = query_test_results(sensor_id, start_time, end_time, page, page_size)
        return success_response(data=results['data'])
    except ValueError as e:
        return error_response(message=f"参数错误: {str(e)}", code=400)
    except Exception as e:
        return error_response(message=str(e), code=500)

@data_bp.route('/data/sensor-data', methods=['GET'])
def get_sensor_data():
    """
    查询原始传感器数据
    """
    try:
        # 获取查询参数
        sensor_id = request.args.get('sensorId')
        source = request.args.get('source')
        start_time = request.args.get('startTime')
        end_time = request.args.get('endTime')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('pageSize', 10))
        
        # 验证参数
        if page_size > 100:
            page_size = 100  # 限制最大页面大小
        
        data = query_sensor_data(sensor_id, source, start_time, end_time, page, page_size)
        return success_response(data=data['data'])
    except ValueError as e:
        return error_response(message=f"参数错误: {str(e)}", code=400)
    except Exception as e:
        return error_response(message=str(e), code=500)

@data_bp.route('/data/export-sensor-data', methods=['GET'])
def export_sensor_data():
    """
    导出原始传感器数据
    """
    try:
        # 获取查询参数
        sensor_id = request.args.get('sensorId')
        source = request.args.get('source')
        start_time = request.args.get('startTime')
        end_time = request.args.get('endTime')
        
        # 验证数据来源参数
        if source and source not in ['simulation', 'real']:
            return error_response(message="数据来源参数不正确，应为 'simulation' 或 'real'", code=400)
        
        # 验证时间参数格式
        if start_time:
            try:
                datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            except ValueError:
                return error_response(message="开始时间格式不正确", code=400)
        
        if end_time:
            try:
                datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            except ValueError:
                return error_response(message="结束时间格式不正确", code=400)
        
        # 这里暂时返回模拟数据，实际实现需要集成文件导出功能
        timestamp = datetime.now().strftime('%Y%m%d')
        return success_response(data={
            "fileUrl": f"/downloads/data/sensor_data_{timestamp}.xlsx",
            "fileName": f"传感器原始数据_{timestamp}.xlsx"
        })
    except Exception as e:
        return error_response(message=str(e), code=500)

@data_bp.route('/data/generate-chart', methods=['GET'])
def generate_chart():
    """
    生成数据图表
    """
    try:
        # 获取查询参数
        sensor_id = request.args.get('sensorId')
        metric = request.args.get('metric')
        start_time = request.args.get('startTime')
        end_time = request.args.get('endTime')
        
        # 验证必需参数
        if not sensor_id or not metric or not start_time or not end_time:
            return error_response(message="缺少必需参数: sensorId, metric, startTime, endTime", code=400)
        
        if metric not in ['temperature', 'humidity']:
            return error_response(message="metric参数必须是temperature或humidity", code=400)
        
        # 验证时间参数格式
        try:
            datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        except ValueError:
            return error_response(message="时间格式不正确，应为ISO 8601格式", code=400)
        
        # 这里暂时返回模拟数据，实际实现需要集成图表生成库
        timestamp = start_time[:10].replace('-', '')
        return success_response(data={
            "chartUrl": f"/charts/{sensor_id}_{metric}_{timestamp}.png",
            "dataPoints": [
                {"time": start_time, "value": 25.3},
                {"time": end_time, "value": 26.1}
            ]
        })
    except Exception as e:
        return error_response(message=str(e), code=500)

# 添加下载路由（模拟）
@data_bp.route('/downloads/<path:filename>', methods=['GET'])
def download_file(filename):
    """
    模拟下载文件
    """
    # 这里只是一个模拟实现，实际应用中需要实现真实的文件下载
    response = make_response(f"模拟下载文件: {filename}")
    response.headers['Content-Type'] = 'application/octet-stream'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response

@data_bp.route('/charts/<path:filename>', methods=['GET'])
def get_chart(filename):
    """
    模拟返回图表
    """
    # 这里只是一个模拟实现，实际应用中需要实现真实的图表服务
    return f"模拟图表: {filename}"