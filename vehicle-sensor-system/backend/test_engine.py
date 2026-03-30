# backend/test_engine.py

def run_content_test(data: dict, config: dict) -> tuple[bool, str]:
    """
    自动化测试引擎 - 车载环境合规性校验模块
    :param data: 传感器数据字典 {"in_car_temp": 26.5, "pm25": 15.2, ...}
    :param config: 测试规则配置字典
    :return: 元组 (是否异常: bool, 错误信息: str)
    """
    errors = []

    # 提取数据 (使用 get 避免 KeyError)
    in_temp = data.get("in_car_temp")
    hum = data.get("humidity")
    pm = data.get("pm25")
    co2 = data.get("co2")

    # 1. 车内温度范围测试
    if in_temp is not None:
        if in_temp < config.get("temp_min", -40.0) or in_temp > config.get("temp_max", 85.0):
            errors.append(f"车内温超限: {in_temp}℃")

    # 2. 车内湿度范围测试
    if hum is not None:
        if hum < config.get("hum_min", 0.0) or hum > config.get("hum_max", 100.0):
            errors.append(f"湿度超限: {hum}%")

    # 3. PM2.5 空气质量测试 (国标：优0-35，良35-75，轻度75-115...)
    pm25_max = config.get("pm25_max", 75.0)
    if pm is not None and pm > pm25_max:
        errors.append(f"PM2.5超标: {pm}ug/m³")

    # 4. CO2 浓度测试 (车内大于1000ppm让人昏沉，大于2000ppm严重超标)
    co2_max = config.get("co2_max", 1000.0)
    if co2 is not None and co2 > co2_max:
        errors.append(f"CO2超标: {co2}ppm")

    is_abnormal = len(errors) > 0
    error_msg = "; ".join(errors)

    return is_abnormal, error_msg