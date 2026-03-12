# crypto_utils.py
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64

# ==========================================
# 密钥配置
# 注意：AES要求密钥必须是 16字节、24字节 或 32字节
# 这里为了演示方便，我们硬编码一个 16位的密钥
# 实际项目中应该从环境变量或配置文件读取
# ==========================================
SECRET_KEY = b'VehicleTest2024!'


def encrypt_data(data_str):
    """
    加密函数
    :param data_str: 明文字符串 (例如 JSON 字符串)
    :return: Base64 编码的密文字符串
    """
    try:
        # 1. 创建 AES Cipher 对象
        # 使用 ECB 模式（简单，不需要偏移量 IV，适合毕设演示）
        cipher = AES.new(SECRET_KEY, AES.MODE_ECB)

        # 2. 数据填充
        # AES 加密要求数据长度必须是 16 的倍数，不够需要填充
        padded_data = pad(data_str.encode('utf-8'), AES.block_size)

        # 3. 加密
        encrypted_bytes = cipher.encrypt(padded_data)

        # 4. 转码
        # 将二进制密文转为 Base64 字符串，方便在 MQTT 中传输
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    except Exception as e:
        print(f"加密出错: {e}")
        return None


def decrypt_data(encrypted_str):
    """
    解密函数
    :param encrypted_str: Base64 编码的密文字符串
    :return: 明文字符串
    """
    try:
        cipher = AES.new(SECRET_KEY, AES.MODE_ECB)

        # 1. Base64 解码
        encrypted_bytes = base64.b64decode(encrypted_str)

        # 2. 解密
        decrypted_padded = cipher.decrypt(encrypted_bytes)

        # 3. 去除填充
        decrypted_data = unpad(decrypted_padded, AES.block_size)

        return decrypted_data.decode('utf-8')
    except Exception as e:
        # 解密失败通常是因为密钥不对或数据被篡改
        print(f"解密失败: {e}")
        return None


# --- 测试代码 (运行 python crypto_utils.py 可测试) ---
if __name__ == "__main__":
    test_json = '{"temp": 25.5}'
    print(f"原始数据: {test_json}")

    enc = encrypt_data(test_json)
    print(f"加密后: {enc}")

    dec = decrypt_data(enc)
    print(f"解密后: {dec}")