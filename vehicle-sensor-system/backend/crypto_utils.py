# crypto_utils.py

import os
import hmac
import hashlib
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# ==========================================
# 密钥配置
# 优先从环境变量读取，方便生产环境部署
# 开发阶段使用默认值，ESP32端需使用相同密钥
#
# 设置环境变量方式：
#   Windows: set AES_SECRET_KEY=VehicleTest2026!
#   Linux:   export AES_SECRET_KEY=VehicleTest2026!
# ==========================================
_KEY_STR = os.environ.get('AES_SECRET_KEY', 'VehicleTest2026!')
SECRET_KEY = _KEY_STR.encode('utf-8')

# AES密钥长度校验（必须是16/24/32字节）
assert len(SECRET_KEY) in (16, 24, 32), (
    f"AES密钥长度必须为16/24/32字节，当前为{len(SECRET_KEY)}字节，"
    f"请检查环境变量 AES_SECRET_KEY"
)

# ==========================================
# 数据包格式说明（CBC模式）
#
# 加密后的数据包结构（Base64解码后）：
# ┌──────────┬────────────────┬──────────────────┐
# │  IV      │   密文          │   HMAC签名        │
# │ 16字节   │   不定长        │   32字节          │
# └──────────┴────────────────┴──────────────────┘
#
# HMAC用于验证数据完整性，防止篡改
# 这也是 case_4_aes_tamper_resistance 的测试依据
# ==========================================

# HMAC签名长度（SHA256输出32字节）
_HMAC_LEN = 32
# IV长度（AES块大小固定16字节）
_IV_LEN = 16


def _compute_hmac(key: bytes, data: bytes) -> bytes:
    """
    计算HMAC-SHA256签名
    :param key:  签名密钥（复用AES密钥）
    :param data: 待签名的数据（密文）
    :return:     32字节签名
    """
    return hmac.new(key, data, hashlib.sha256).digest()


def encrypt_data(data_str: str) -> str | None:
    """
    加密函数（AES-CBC + HMAC完整性签名）

    :param data_str: 明文字符串（例如JSON字符串）
    :return:         Base64编码的密文字符串，失败返回None

    数据包结构: Base64( IV[16] + 密文[N] + HMAC[32] )
    """
    try:
        # 1. 生成随机IV（每次加密不同，防止相同明文产生相同密文）
        iv = os.urandom(_IV_LEN)

        # 2. 创建AES-CBC加密器
        cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)

        # 3. PKCS7填充 + 加密
        padded_data = pad(data_str.encode('utf-8'), AES.block_size)
        encrypted_bytes = cipher.encrypt(padded_data)

        # 4. 计算HMAC签名（对密文签名，而不是明文）
        mac = _compute_hmac(SECRET_KEY, encrypted_bytes)

        # 5. 拼接: IV + 密文 + HMAC，转Base64
        payload = iv + encrypted_bytes + mac
        return base64.b64encode(payload).decode('utf-8')

    except Exception as e:
        print(f"[crypto] 加密出错: {e}")
        return None


def decrypt_data(encrypted_str: str) -> str | None:
    """
    解密函数（AES-CBC + HMAC完整性校验）

    :param encrypted_str: Base64编码的密文字符串
    :return:              明文字符串，失败或校验不通过返回None

    返回None的情况：
      - Base64格式非法
      - 数据包长度不足（被截断或伪造）
      - HMAC校验失败（数据被篡改）  ← case_4测试的就是这个
      - AES解密失败（密钥错误）
      - 填充格式非法
    """
    try:
        # 1. Base64解码
        raw = base64.b64decode(encrypted_str)

        # 2. 长度校验（至少需要 IV + 1个AES块 + HMAC）
        min_len = _IV_LEN + AES.block_size + _HMAC_LEN
        if len(raw) < min_len:
            print(f"[crypto] 数据包长度不足: {len(raw)} < {min_len}，疑似伪造数据")
            return None

        # 3. 拆分数据包
        iv            = raw[:_IV_LEN]
        encrypted_bytes = raw[_IV_LEN: -_HMAC_LEN]
        received_mac  = raw[-_HMAC_LEN:]

        # 4. HMAC完整性校验（使用恒定时间比较，防止时序攻击）
        expected_mac = _compute_hmac(SECRET_KEY, encrypted_bytes)
        if not hmac.compare_digest(received_mac, expected_mac):
            print("[crypto] HMAC校验失败，数据可能被篡改，已拒绝")
            return None

        # 5. AES-CBC解密
        cipher = AES.new(SECRET_KEY, AES.MODE_CBC, iv)
        decrypted_padded = cipher.decrypt(encrypted_bytes)

        # 6. 去除填充
        decrypted_data = unpad(decrypted_padded, AES.block_size)
        return decrypted_data.decode('utf-8')

    except (ValueError, KeyError) as e:
        # 填充错误或格式错误，通常是被篡改导致的
        print(f"[crypto] 解密失败（填充/格式异常）: {e}")
        return None
    except Exception as e:
        print(f"[crypto] 解密失败（未知异常）: {e}")
        return None


# ==========================================
# 自测代码
# 运行: python crypto_utils.py
# ==========================================
if __name__ == "__main__":
    print("=" * 50)
    print("crypto_utils 自测")
    print("=" * 50)

    # 测试1：正常加解密
    print("\n【测试1】正常加解密")
    original = '{"sensor_id": "ENV_SIM_001", "in_car_temp": 25.5}'
    print(f"原始数据: {original}")
    enc = encrypt_data(original)
    print(f"加密结果: {enc}")
    dec = decrypt_data(enc)
    print(f"解密结果: {dec}")
    assert dec == original, "❌ 测试1失败"
    print("✅ 测试1通过")

    # 测试2：相同明文两次加密结果不同（CBC随机IV）
    print("\n【测试2】相同明文两次加密结果不同")
    enc1 = encrypt_data(original)
    enc2 = encrypt_data(original)
    print(f"第一次: {enc1[:30]}...")
    print(f"第二次: {enc2[:30]}...")
    assert enc1 != enc2, "❌ 测试2失败（IV未随机化）"
    print("✅ 测试2通过")

    # 测试3：篡改数据后解密失败（对应case_4测试用例）
    print("\n【测试3】篡改数据应被拒绝")
    tamper_cases = [
        ("随机伪造字符串",       "dGVzdF9hbHRlcmVkX3N0cmluZw=="),
        ("空字符串",             ""),
        ("合法Base64但内容错误", "aGVsbG8gd29ybGQ="),
    ]
    for desc, fake in tamper_cases:
        result = decrypt_data(fake)
        status = "✅ 已拒绝" if result is None else "❌ 防线失效"
        print(f"  场景[{desc}]: {status}")

    # 测试4：密文被修改一位后校验失败
    print("\n【测试4】密文被篡改一位后应被拒绝")
    enc_bytes = bytearray(base64.b64decode(enc))
    enc_bytes[20] ^= 0xFF          # 翻转第20字节
    tampered = base64.b64encode(bytes(enc_bytes)).decode()
    result = decrypt_data(tampered)
    assert result is None, "❌ 测试4失败（篡改未被检测到）"
    print("✅ 测试4通过：篡改被成功检测")

    print("\n" + "=" * 50)
    print("全部自测通过 ✅")
    print("=" * 50)
