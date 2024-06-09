from __future__ import annotations
from typing import Callable
from uuid import uuid4


# --- private methods --- #
def __uuid() -> str:
    return str(uuid4())


# --- facade --- #

uuid: Callable[[], str] = __uuid


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
