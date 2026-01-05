"""
测试用例控制器
"""
from flask import Blueprint
from utils.response import success_response, error_response
from services.test_case_service import get_test_cases

# 创建蓝图
test_case_bp = Blueprint('test_case', __name__, url_prefix='/api/v1')

@test_case_bp.route('/test-cases', methods=['GET'])
def get_test_cases_list():
    """
    获取测试用例列表
    """
    try:
        test_cases = get_test_cases()
        return success_response(data=test_cases)
    except Exception as e:
        return error_response(message=str(e), code=500)