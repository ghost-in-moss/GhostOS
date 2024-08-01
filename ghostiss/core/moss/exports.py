from typing import Dict, Optional, Iterable, List, Any
from copy import deepcopy
from ghostiss.core.moss.reflect import (
    Reflection, Attr, reflects,
    ClassSign, Model,
    Interface, Typing,
    IterableReflection,
)
from ghostiss.helpers import get_calling_module

__all__ = [
    'EXPORTS_KEY', 'Exporter'
]

EXPORTS_KEY = "EXPORTS"
"""如果一个 module 里包含 EXPORTS 变量, 同时是一个 Exports 对象, 则 modules 模块会优先从中获取"""


class Exporter(IterableReflection):
    """
    提供一套语法糖方便做链式的 Exports 构建.
    这是一种对类库的封装做法.
    todo:
    1. 可以描述模块
    2. 可以快速生成基本抽象.
    """

    def __init__(
            self, *,
            modulename: Optional[str] = None,
            with_module: bool = True,
            deep_copy: bool = True,
    ):
        self.module: Optional[str] = modulename
        if modulename is None and with_module:
            self.module = get_calling_module(2)
        self.__deep_copy = deep_copy
        self.__reflections: Dict[str, Reflection] = {}
        self.__reflection_orders: List[str] = []
        super().__init__(name="")

    def reflects(self, *args, **kwargs) -> "Exporter":
        items = []
        for item in reflects(*args, **kwargs):
            items.append(item)
        return self.with_reflection(*items)

    def iterate(self) -> Iterable[Reflection]:
        return self.all()

    def value(self) -> Dict[str, Any]:
        return self.__reflections

    def prompt(self) -> str:
        lines = []
        for reflection in self.iterate():
            lines.append(reflection.prompt())
        return "\n\n".join(lines)

    def attr(self, name: str, value: Any, typehint: Optional[Any] = None) -> "Exporter":
        attr = Attr(name=name, value=value, typehint=typehint)
        return self.with_reflection(attr)

    def with_reflection(self, *reflections: Reflection) -> "Exporter":
        for reflection in reflections:
            if self.module:
                # 先深拷贝, 避免污染.
                reflection = deepcopy(reflection)
                reflection = reflection.update(module=self.module)

            name = reflection.name()
            self.__reflection_orders.append(name)
            self.__reflections[name] = reflection
        return self

    def model(self, model: type, alias: Optional[str] = None) -> "Exporter":
        m = Model(model=model, name=alias)
        return self.with_reflection(m)

    def interface(self, cls: type, alias: str = None) -> "Exporter":
        lib = Interface(cls=cls, name=alias)
        return self.with_reflection(lib)

    def typing(self, typing: Any, alias: str) -> "Exporter":
        r = Typing(typing=typing, name=alias)
        return self.with_reflection(r)

    def class_sign(self, cls: type, alias: str = None) -> "Exporter":
        itf = ClassSign(cls=cls, name=alias)
        return self.with_reflection(itf)

    def get(self, name: str) -> Optional[Reflection]:
        reflection = self.__reflections.get(name, None)
        # 每次调用都深拷贝一下, 是不是必要的?
        if self.__deep_copy and reflection is not None:
            return deepcopy(reflection)
        return reflection

    def all(self) -> Iterable[Reflection]:
        for name in self.__reflection_orders:
            re = self.get(name)
            if re:
                yield re
