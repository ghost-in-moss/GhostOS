import hashlib


def md5(input_string: str) -> str:
    # 创建一个md5对象
    md5_obj = hashlib.md5()
    # 将输入字符串编码为字节，因为md5需要字节输入
    md5_obj.update(input_string.encode('utf-8'))
    # 获取16进制的哈希值
    hash_value = md5_obj.hexdigest()
    return hash_value
