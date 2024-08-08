from typing import Dict, Optional, Iterable, List, Any, Callable, Type
from copy import deepcopy
from ghostiss.core.moss_p1.reflect import (
    Reflection, Attr, reflects,
    ClassSign, SourceCode,
    Interface, Typing,
    IterableReflection,
    get_calling_modulename, is_typing,
)

__all__ = [
    'EXPORTS_KEY', 'Exporter'
]

EXPORTS_KEY = "EXPORTS"
"""如果一个 module 里包含 EXPORTS 变量, 同时是一个 Exports 对象, 则 modules 模块会优先从中获取"""


class Exporter(IterableReflection):
    """
    提供一套语法糖方便做链式的 Exports 构建.
    这是一种对类库的封装做法.
    1. 可以描述模块
    2. 可以快速生成基本抽象.

    Exporter 提供的各种方法用于将一个变量改造成 Reflection 对象
    并支持其它包引用它.
    这个包本身也可以看作是 reflect 包的语法糖. 会提供更简洁一些 api 方便快速生成.
    """

    def __init__(
            self, *,
            modulename: Optional[str] = None,
            with_module: bool = True,
            deep_copy: bool = False,
    ):
        """
        初始化一个 Exporter.
        它本身也是 IterableReflection, 可以直接作为 Reflection 使用, 比如添加到 MOSS.
        :param modulename: 人工指定一个 modulename, 所有的 reflection 的 module 都会替换成它.
        :param with_module: 如果没有人工指定 modulename, 则默认会根据 Exporter 调用位置生成一个.
        :param deep_copy: 如果开启了 deepcopy, 所有的 reflection 返回前会深拷贝. 避免交叉污染.
        """
        self.module: Optional[str] = modulename
        if modulename is None and with_module:
            self.module = get_calling_modulename(2)
        self.__deep_copy = deep_copy
        self.__reflections: Dict[str, Reflection] = {}
        self.__reflection_orders: List[str] = []
        super().__init__(name="")

    def reflects(self, *args, **kwargs) -> "Exporter":
        """
        主动将各种变量映射成 Reflection 并输出.
        使用系统默认的加工方式.
        :param args: 必须是具有 __name__ 的变量, 否则会抛出异常.
        :param kwargs: alias=>value, 生成的 Reflection 会重命名.
        :return: 链式调用.
        """
        items = []
        for item in reflects(*args, **kwargs):
            items.append(item)
        return self.with_reflection(*items)

    def iterate(self) -> Iterable[Reflection]:
        """
        遍历 Exporter 内包含的所有 Reflection.
        """
        return self.all()

    def value(self) -> Dict[str, Any]:
        """
        将所有 Reflection 的真值作为一个字典输出.
        """
        data = {}
        for reflection in self.all():
            data[reflection.name()] = reflection.value()
        return data

    def prompt(self) -> str:
        """
        Exporter 自身的 Prompt 描述
        todo: 将它实现对一个包的描述.
        """
        lines = []
        for reflection in self.iterate():
            lines.append(reflection.prompt())
        return "\n\n".join(lines)

    def with_reflection(self, *reflections: Reflection) -> "Exporter":
        """
        添加一个或多个已经完成加工处理的 Reflection.
        """
        for reflection in reflections:
            module_spec = reflection.name()
            if self.module:
                # 先深拷贝, 避免污染.
                reflection = deepcopy(reflection)
                reflection = reflection.update(module=self.module, module_spec=module_spec)

            name = reflection.name()
            self.__reflection_orders.append(name)
            self.__reflections[name] = reflection
        return self

    def attr(
            self,
            name: str,
            value: Any,
            typehint: Optional[Any] = None,
            mod: Optional[Callable[[Attr], Attr]] = None,
    ) -> "Exporter":
        """
        将一个值 (通常是 object) 作为一个属性输出.
        适合输出 module 里的常量. 比如
        a = 123
        b = Union[int]
        CONSTS_NAME = "some_value"
        library = ClassName(*args)

        这样输出的值被其它包引用时, 修改可能会污染原始值.

        :param name: 如果作为属性输出, 则必须有一个指定的属性名.
        :param value: 通常是各种类型的实例.
        :param typehint: 给 Attr 指定一个类型描述, 如果给定了, 则生成 prompt 时展示的类型是这个.
        :param mod: 可以用来修改生成的 Attr, 添加更多想要的逻辑.

        # todo: 添加更多属性.
        """
        attr = Attr(name=name, value=value, typehint=typehint)
        if mod is not None:
            attr = mod(attr)
        return self.with_reflection(attr)

    def source_code(self, cls: Type, typehint: Optional[Type] = None, alias: Optional[str] = None) -> "Exporter":
        """
        Export source code of a class.
        :param cls: a class type
        :param typehint: if given, the prompt will show source code of the typehint but rename it with cls
        :param alias: if given, the prompt will rename to alias
        """
        m = SourceCode(cls=cls, name=alias, typehint=typehint)
        return self.with_reflection(m)

    def interface(self, cls: type, alias: str = None) -> "Exporter":
        lib = Interface(cls=cls, name=alias)
        return self.with_reflection(lib)

    def typing(self, typing: Any, alias: str) -> "Exporter":
        if not is_typing(typing):
            raise AttributeError(f'{typing} is not a typing which is extended from typing.')
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
                if self.__deep_copy:
                    re = deepcopy(re)
                yield re
