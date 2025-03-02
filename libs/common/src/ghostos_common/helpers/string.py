
def camel_to_snake(name: str) -> str:
    buffer = ""
    result = ""
    for c in name:
        if 'A' <= c <= 'Z':
            buffer += c
            continue
        buffer_len = len(buffer)
        if buffer_len == 0:
            result += c
        elif buffer_len == 1:
            prefix = '_' if result else ''
            result += prefix + buffer.lower() + c
            buffer = ""
        else:
            prefix = '_' if result else ''
            result += prefix + buffer[:buffer_len - 1].lower() + '_' + buffer[buffer_len - 1] + c
            buffer = ""

    if len(buffer) > 0:
        prefix = '_' if result else ''
        result += prefix + buffer.lower()
    return result
