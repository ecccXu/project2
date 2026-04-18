# backend/test_engine.py

# ==========================================
# 传感器数据合规性校验引擎
#
# 职责：
#   作为系统第一层测试能力
#   每条从MQTT接收到的传感器数据都经过此模块校验
#   判定数据是否在合规范围内，结果写入数据库
#
# 在系统中的位置：
#   MQTT消息到达
#       ↓
#   on_message() 解密解析          ← main.py
#       ↓
#   run_content_test() 合规校验    ← 本模块（此处）
#       ↓
#   _save_to_db() 写库             ← main.py
#
# 与 test_bench.py 的区别：
#   test_engine：被动式校验，数据进来就检查，无需下发指令
#   test_bench ：主动式测试，下发指令观察响应，验证动态性能
# ==========================================


# ==========================================
# 默认阈值配置
#
# 设计依据：
#   温度范围：参考 ISO 16750 车载电子设备环境条件
#             车内传感器工作范围 -40℃ ~ 85℃
#   湿度范围：0% ~ 100% 物理极限
#   PM2.5：   参考《环境空气质量标准》GB 3095-2012
#             优：0~35，良：35~75，轻度污染：75~115
#             车内以"良"上限 75 μg/m³ 为告警阈值
#   CO2：     参考《室内空气质量标准》GB/T 18883-2002
#             正常室内 < 1000 ppm
#             车内 > 1000 ppm 人会感到困倦，> 2000 ppm 严重超标
#
# 可通过 /api/config/thresholds 接口动态修改（main.py第5步实现）
# ==========================================
DEFAULT_TEST_CONFIG = {
    # 车内温度（℃）
    "in_temp_min":   -40.0,
    "in_temp_max":    85.0,

    # 车外温度（℃）
    "out_temp_min":  -40.0,
    "out_temp_max":   85.0,

    # 车内湿度（%RH）
    "hum_min":         0.0,
    "hum_max":       100.0,

    # PM2.5（μg/m³）
    # 超过75为轻度污染，触发告警
    "pm25_max":       75.0,

    # CO2浓度（ppm）
    # 超过1000ppm触发告警
    "co2_max":      1000.0,
}


def run_content_test(data: dict, config: dict = None) -> tuple[bool, str]:
    """
    传感器数据合规性校验（第一层测试能力）

    :param data:   传感器数据字典，来自 main.py 的 parsed_item
                   {
                       "in_car_temp":  25.5,
                       "out_car_temp": 20.0,
                       "humidity":     55.0,
                       "pm25":         30.0,
                       "co2":          600.0,
                       ...
                   }
    :param config: 阈值配置字典，为None时使用 DEFAULT_TEST_CONFIG
                   支持部分覆盖，未传入的key使用默认值

    :return: 元组 (is_abnormal: bool, error_msg: str)
             is_abnormal = True  表示存在超标项
             error_msg   = ""    表示全部正常
             error_msg   = "车内温超限: 90.0℃; CO2超标: 1500.0ppm"
                           多个问题用分号分隔
    """
    # 合并配置：用传入的config覆盖默认值，支持部分覆盖
    final_config = DEFAULT_TEST_CONFIG.copy()
    if config:
        final_config.update(config)

    errors = []

    # 提取数据字段（用get避免KeyError，缺失字段跳过校验）
    in_temp  = data.get("in_car_temp")
    out_temp = data.get("out_car_temp")
    hum      = data.get("humidity")
    pm       = data.get("pm25")
    co2      = data.get("co2")

    # ==========================================
    # 校验1：车内温度范围
    # ==========================================
    if in_temp is not None:
        if in_temp < final_config["in_temp_min"]:
            errors.append(
                f"车内温过低: {in_temp}℃ "
                f"(下限: {final_config['in_temp_min']}℃)"
            )
        elif in_temp > final_config["in_temp_max"]:
            errors.append(
                f"车内温超限: {in_temp}℃ "
                f"(上限: {final_config['in_temp_max']}℃)"
            )

    # ==========================================
    # 校验2：车外温度范围
    # 旧版缺失此校验，本次补全
    # ==========================================
    if out_temp is not None:
        if out_temp < final_config["out_temp_min"]:
            errors.append(
                f"车外温过低: {out_temp}℃ "
                f"(下限: {final_config['out_temp_min']}℃)"
            )
        elif out_temp > final_config["out_temp_max"]:
            errors.append(
                f"车外温超限: {out_temp}℃ "
                f"(上限: {final_config['out_temp_max']}℃)"
            )

    # ==========================================
    # 校验3：车内湿度范围
    # ==========================================
    if hum is not None:
        if hum < final_config["hum_min"]:
            errors.append(
                f"湿度过低: {hum}% "
                f"(下限: {final_config['hum_min']}%)"
            )
        elif hum > final_config["hum_max"]:
            errors.append(
                f"湿度超限: {hum}% "
                f"(上限: {final_config['hum_max']}%)"
            )

    # ==========================================
    # 校验4：PM2.5 空气质量
    # 参考 GB 3095-2012：75 μg/m³ 为良/轻度污染分界线
    # ==========================================
    if pm is not None:
        if pm > final_config["pm25_max"]:
            errors.append(
                f"PM2.5超标: {pm}μg/m³ "
                f"(上限: {final_config['pm25_max']}μg/m³)"
            )

    # ==========================================
    # 校验5：CO2 浓度
    # 参考 GB/T 18883-2002：1000 ppm 为告警阈值
    # ==========================================
    if co2 is not None:
        if co2 > final_config["co2_max"]:
            errors.append(
                f"CO2超标: {co2}ppm "
                f"(上限: {final_config['co2_max']}ppm)"
            )

    is_abnormal = len(errors) > 0
    error_msg   = "; ".join(errors)

    return is_abnormal, error_msg


def get_default_config() -> dict:
    """
    获取默认阈值配置的副本
    供 main.py 的 /api/config/thresholds 接口使用
    返回副本而不是原始对象，防止外部误修改默认值
    """
    return DEFAULT_TEST_CONFIG.copy()


# ==========================================
# 自测代码
# Windows运行方式：
#   cd backend
#   python test_engine.py
# ==========================================
if __name__ == "__main__":
    print("=" * 50)
    print("test_engine.py 自测")
    print("Windows环境")
    print("=" * 50)

    # 测试1：全部正常数据
    print("\n【测试1】全部正常数据")
    normal_data = {
        "in_car_temp":  25.0,
        "out_car_temp": 20.0,
        "humidity":     55.0,
        "pm25":         30.0,
        "co2":          600.0,
    }
    is_ab, msg = run_content_test(normal_data)
    assert is_ab is False, f"❌ 测试1失败，正常数据被判为异常: {msg}"
    assert msg == ""
    print(f"  数据: {normal_data}")
    print(f"  结果: is_abnormal={is_ab}, error_msg='{msg}'")
    print("  ✅ 测试1通过")

    # 测试2：车内温度超限
    print("\n【测试2】车内温度超限")
    temp_data = {
        "in_car_temp":  90.0,   # 超过85℃上限
        "out_car_temp": 20.0,
        "humidity":     55.0,
        "pm25":         30.0,
        "co2":          600.0,
    }
    is_ab, msg = run_content_test(temp_data)
    assert is_ab is True, "❌ 测试2失败，超温未被检测"
    assert "车内温超限" in msg
    print(f"  数据: in_car_temp=90.0℃")
    print(f"  结果: is_abnormal={is_ab}, error_msg='{msg}'")
    print("  ✅ 测试2通过")

    # 测试3：车外温度过低
    print("\n【测试3】车外温度过低")
    out_temp_data = {
        "in_car_temp":  25.0,
        "out_car_temp": -50.0,  # 低于-40℃下限
        "humidity":     55.0,
        "pm25":         30.0,
        "co2":          600.0,
    }
    is_ab, msg = run_content_test(out_temp_data)
    assert is_ab is True, "❌ 测试3失败，车外低温未被检测"
    assert "车外温过低" in msg
    print(f"  数据: out_car_temp=-50.0℃")
    print(f"  结果: is_abnormal={is_ab}, error_msg='{msg}'")
    print("  ✅ 测试3通过")

    # 测试4：PM2.5 + CO2 同时超标（多项异常）
    print("\n【测试4】PM2.5 + CO2 同时超标")
    pollution_data = {
        "in_car_temp":  25.0,
        "out_car_temp": 26.0,
        "humidity":     45.0,
        "pm25":         180.0,  # 隧道工况，严重超标
        "co2":          2200.0, # 隧道工况，严重超标
    }
    is_ab, msg = run_content_test(pollution_data)
    assert is_ab is True, "❌ 测试4失败，污染未被检测"
    assert "PM2.5超标" in msg
    assert "CO2超标" in msg
    print(f"  数据: pm25=180.0, co2=2200.0 (隧道工况)")
    print(f"  结果: is_abnormal={is_ab}, error_msg='{msg}'")
    print("  ✅ 测试4通过")

    # 测试5：使用自定义阈值配置
    print("\n【测试5】自定义阈值配置")
    custom_config = {"pm25_max": 200.0}  # 放宽PM2.5阈值
    is_ab, msg = run_content_test(pollution_data, config=custom_config)
    # pm25=180 < 200，不再超标；但co2=2200 > 1000，仍超标
    assert "PM2.5超标" not in msg, "❌ 测试5失败，自定义阈值未生效"
    assert "CO2超标" in msg
    print(f"  自定义配置: pm25_max=200.0")
    print(f"  结果: is_abnormal={is_ab}, error_msg='{msg}'")
    print("  ✅ 测试5通过（PM2.5阈值放宽，CO2仍告警）")

    # 测试6：缺失字段跳过校验（ESP32可能不上报所有字段）
    print("\n【测试6】缺失字段跳过校验")
    partial_data = {
        "in_car_temp": 25.0,
        # 其他字段缺失，模拟ESP32只上报温度的场景
    }
    is_ab, msg = run_content_test(partial_data)
    assert is_ab is False
    print(f"  数据: 仅有 in_car_temp=25.0，其他字段缺失")
    print(f"  结果: is_abnormal={is_ab}, error_msg='{msg}'")
    print("  ✅ 测试6通过（缺失字段不报错）")

    # 测试7：get_default_config 返回副本
    print("\n【测试7】get_default_config 返回副本验证")
    cfg = get_default_config()
    cfg["pm25_max"] = 9999.0   # 修改副本
    assert DEFAULT_TEST_CONFIG["pm25_max"] == 75.0, "❌ 测试7失败，原始配置被污染"
    print(f"  修改副本后原始值: pm25_max={DEFAULT_TEST_CONFIG['pm25_max']}")
    print("  ✅ 测试7通过（原始配置未被污染）")

    print("\n" + "=" * 50)
    print("全部自测通过 ✅")
    print("=" * 50)
