from __future__ import annotations

from abc import ABC, abstractmethod


INSTRUCTION = """
系统里必须依赖的底层模块. 比如 Cache 之类的? 
"""


class Cache(ABC):
    """
    比如有个模块叫 cache
    """


class Config(ABC):
    """
    假设可以固定的获取配置.
    """