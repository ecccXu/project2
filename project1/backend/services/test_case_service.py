"""
测试用例服务
"""
from backend.models import TestCase
from backend.config.db_config import db
from sqlalchemy.exc import IntegrityError


def get_test_cases():
    """
    获取测试用例列表
    """
    test_cases = TestCase.query.all()
    result = []
    for case in test_cases:
        result.append({
            "caseId": case.case_id,
            "name": case.name,
            "type": case.type,
            "description": case.description,
            "enabled": case.enabled
        })
    return result


def initialize_default_test_cases():
    """
    初始化默认测试用例
    """
    from flask import current_app
    from backend.models import TestCase
    from backend.config.db_config import db
    
    with current_app.app_context():
        default_cases = [
            {
                "case_id": "TC-001",
                "name": "温度范围校验",
                "type": "功能测试",
                "description": "校验温度值是否在车载工作范围 [-40℃, 85℃] 内",
                "enabled": True
            },
            {
                "case_id": "TC-002",
                "name": "湿度范围校验",
                "type": "功能测试",
                "description": "校验湿度值是否在有效范围 [0%, 100%] 内",
                "enabled": True
            },
            {
                "case_id": "TC-003",
                "name": "数据格式校验",
                "type": "功能测试",
                "description": "校验接收的数据是否为合法JSON格式，并包含sensorId、temperature等必要字段",
                "enabled": True
            },
            {
                "case_id": "TC-004",
                "name": "MQTT QoS 1 可靠性测试",
                "type": "协议测试",
                "description": "模拟网络中断，验证QoS 1级别下消息的送达性",
                "enabled": False
            }
        ]
        
        # 检查是否已有测试用例，避免重复初始化
        existing_count = TestCase.query.count()
        if existing_count > 0:
            current_app.logger.info(f"跳过初始化测试用例，已存在 {existing_count} 个测试用例")
            return
        
        # 添加默认测试用例
        for case_data in default_cases:
            case = TestCase(
                case_id=case_data['case_id'],
                name=case_data['name'],
                type=case_data['type'],
                description=case_data['description'],
                enabled=case_data['enabled']
            )
            db.session.add(case)
        
        db.session.commit()
        current_app.logger.info(f"成功初始化 {len(default_cases)} 个默认测试用例")