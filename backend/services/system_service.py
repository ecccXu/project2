"""
系统状态服务
"""
from backend.models import SystemStatus, Sensor, TestResult
from backend.config.db_config import db
from datetime import datetime, timedelta
from backend.utils.response import success_response


def get_system_status():
    """
    获取系统整体状态
    """
    try:
        # 查询最新的系统状态记录
        latest_status = SystemStatus.query.order_by(SystemStatus.updated_at.desc()).first()
        
        if latest_status:
            # 如果存在记录，返回最新的状态
            return {
                "systemStatus": latest_status.system_status,
                "connectedSensors": latest_status.connected_sensors,
                "testPassRate": latest_status.test_pass_rate,
                "todayTestCount": latest_status.today_test_count,
                "mqttConnectionStatus": latest_status.mqtt_connection_status
            }
        else:
            # 如果没有记录，返回默认值
            # 计算今日测试总数
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_test_count = TestResult.query.filter(TestResult.test_time >= today_start).count()
            
            # 计算连接的传感器数量
            connected_sensors = Sensor.query.filter(Sensor.status == 'running').count()
            
            # 计算测试通过率
            total_tests = TestResult.query.filter(TestResult.test_time >= today_start).count()
            passed_tests = TestResult.query.filter(
                TestResult.test_time >= today_start,
                TestResult.result == 'pass'
            ).count()
            
            test_pass_rate = 0
            if total_tests > 0:
                test_pass_rate = round((passed_tests / total_tests) * 100, 2)
            
            # 创建新的系统状态记录
            new_status = SystemStatus(
                system_status='online',
                connected_sensors=connected_sensors,
                test_pass_rate=test_pass_rate,
                today_test_count=today_test_count,
                mqtt_connection_status='connected'
            )
            
            db.session.add(new_status)
            db.session.commit()
            
            return {
                "systemStatus": new_status.system_status,
                "connectedSensors": new_status.connected_sensors,
                "testPassRate": new_status.test_pass_rate,
                "todayTestCount": new_status.today_test_count,
                "mqttConnectionStatus": new_status.mqtt_connection_status
            }
    except Exception as e:
        # 如果出现错误，返回默认值
        print(f"获取系统状态时出现错误: {e}")
        return {
            "systemStatus": "offline",
            "connectedSensors": 0,
            "testPassRate": 0,
            "todayTestCount": 0,
            "mqttConnectionStatus": "disconnected"
        }


def update_system_status():
    """
    更新系统状态
    """
    try:
        # 计算今日测试总数
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_test_count = TestResult.query.filter(TestResult.test_time >= today_start).count()
        
        # 计算连接的传感器数量
        connected_sensors = Sensor.query.filter(Sensor.status == 'running').count()
        
        # 计算测试通过率
        total_tests = TestResult.query.filter(TestResult.test_time >= today_start).count()
        passed_tests = TestResult.query.filter(
            TestResult.test_time >= today_start,
            TestResult.result == 'pass'
        ).count()
        
        test_pass_rate = 0
        if total_tests > 0:
            test_pass_rate = round((passed_tests / total_tests) * 100, 2)
        
        # 获取最新的系统状态记录
        latest_status = SystemStatus.query.order_by(SystemStatus.updated_at.desc()).first()
        
        if latest_status:
            # 更新现有记录
            latest_status.connected_sensors = connected_sensors
            latest_status.test_pass_rate = test_pass_rate
            latest_status.today_test_count = today_test_count
            latest_status.updated_at = datetime.utcnow()
        else:
            # 创建新记录
            new_status = SystemStatus(
                system_status='online',
                connected_sensors=connected_sensors,
                test_pass_rate=test_pass_rate,
                today_test_count=today_test_count,
                mqtt_connection_status='connected'
            )
            db.session.add(new_status)
        
        db.session.commit()
    except Exception as e:
        print(f"更新系统状态时出现错误: {e}")
        db.session.rollback()
