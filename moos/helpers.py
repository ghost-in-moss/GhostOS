from typing import Dict


def dict_without_none(data: dict) -> dict:
    result = {}
    for key, value in data.items():
        if value is not None:
            result[key] = value
    return result


def dict_without_zero(data: dict) -> dict:
    result = {}
    for key, value in data.items():
        if not value:
            result[key] = value
    return result
