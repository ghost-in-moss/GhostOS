def dict_without_none(data: dict) -> dict:
    """
    Removes None values from a dictionary.
    """
    result = {}
    for key, value in data.items():
        if value is not None:
            result[key] = value
    return result


def dict_without_zero(data: dict) -> dict:
    """
    Removes zero values from a dictionary.
    """
    result = {}
    for key, value in data.items():
        if not value:
            result[key] = value
    return result
