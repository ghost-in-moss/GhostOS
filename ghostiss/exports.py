from typing import Dict, Optional
from ghostiss.reflect import (
    Reflection, reflects,
    Library,
)

__all__ = [
    'EXPORTS_KEY', 'Exports'
]

EXPORTS_KEY = "EXPORTS"
"""如果一个 module 里包含 EXPORTS 变量, 同时是一个 Exports 对象, 则 modules 模块会优先从中获取"""


class Exports:
    """
    提供一套语法糖方便做链式的 Exports 构建.
    这是一种对类库的封装做法.
    todo:
    1. 可以描述模块
    2. 可以快速生成基本抽象.
    """

    def __init__(self, *args, **kwargs):
        reflections = reflects(*args, **kwargs)
        self.__reflections: Dict[str, Reflection] = {}
        for reflection in reflections:
            self.__reflections[reflection.name()] = reflection

    def with_lib(self, cls: type, alias: str = None) -> "Exports":
        lib = Library(cls=cls, alias=alias)
        self.__reflections[lib.name()] = lib
        return self

    def get(self, name: str) -> Optional[Reflection]:
        return self.__reflections.get(name, None)
