"""
测试执行控制器
"""
from flask import Blueprint, request
from backend.utils.response import success_response, error_response
from backend.services.test_execution_service import start_test, get_realtime_results
from datetime import datetime

# 创建蓝图
test_execution_bp = Blueprint('test_execution', __name__, url_prefix='/api/v1')

@test_execution_bp.route('/tests/start', methods=['POST'])
def start_test_execution():
    """
    开始测试
    """
    try:
        test_data = request.get_json()
        if not test_data:
            return error_response(message="请求体不能为空", code=400)
        
        required_fields = ['sensorId', 'caseIds']
        for field in required_fields:
            if field not in test_data:
                return error_response(message=f"缺少必需字段: {field}", code=400)
        
        if not isinstance(test_data['caseIds'], list):
            return error_response(message="caseIds必须是数组", code=400)
        
        if len(test_data['caseIds']) == 0:
            return error_response(message="caseIds不能为空数组", code=400)
        
        result = start_test(test_data)
        return success_response(data=result, message="测试已开始")
    except ValueError as e:
        error_code = 603 if "测试任务冲突" in str(e) else 400
        return error_response(message=str(e), code=error_code)
    except Exception as e:
        return error_response(message=str(e), code=500)

@test_execution_bp.route('/tests/realtime-results', methods=['GET'])
def get_realtime_test_results():
    """
    获取实时测试结果
    """
    try:
        sensor_id = request.args.get('sensorId')
        results = get_realtime_results(sensor_id)
        return success_response(data=results)
    except Exception as e:
        return error_response(message=str(e), code=500)

@test_execution_bp.route('/tests/export-report', methods=['GET'])
def export_test_report():
    """
    导出测试报告
    """
    try:
        # 获取查询参数
        test_id = request.args.get('testId')
        format_type = request.args.get('format')
        
        if not format_type:
            return error_response(message="缺少format参数", code=400)
        
        if format_type not in ['pdf', 'excel']:
            return error_response(message="format参数必须是pdf或excel", code=400)
        
        # 验证testId格式（如果提供了testId）
        if test_id and not test_id.startswith('T-'):
            return error_response(message="testId格式不正确", code=400)
        
        # 这里暂时返回模拟数据，实际实现需要集成报告生成库
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_id = test_id if test_id else 'all_tests'
        return success_response(data={
            "reportUrl": f"/downloads/reports/{report_id}.{format_type}",
            "fileName": f"测试报告_{timestamp}.{format_type}"
        })
    except Exception as e:
        return error_response(message=str(e), code=500)