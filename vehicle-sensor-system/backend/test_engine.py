# backend/test_engine.py

def run_content_test(data: dict, config: dict) -> tuple[bool, str]:
    """
    自动化测试引擎 - 内容合规性校验模块
    :param data: 传感器数据字典，例如 {"temperature": 25.0, "humidity": 60.0}
    :param config: 测试规则配置字典
    :return: 元组 (是否异常: bool, 错误信息: str)
    """
    errors = []
    temp = data.get('temperature')
    hum = data.get('humidity')

    # 1. 温度范围测试 (安全获取配置，设置默认值防止报错)
    temp_min = config.get("temp_min", -40.0)
    temp_max = config.get("temp_max", 85.0)

    if temp is not None and (temp < temp_min or temp > temp_max):
        errors.append(f"温度超限: {temp}℃")

    # 2. 湿度范围测试
    hum_min = config.get("hum_min", 0.0)
    hum_max = config.get("hum_max", 100.0)

    if hum is not None and (hum < hum_min or hum > hum_max):
        errors.append(f"湿度非法: {hum}%")

    is_abnormal = len(errors) > 0
    error_msg = "; ".join(errors)

    return is_abnormal, error_msg