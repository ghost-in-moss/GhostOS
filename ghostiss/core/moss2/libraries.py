from abc import ABC, abstractmethod
from types import ModuleType
from importlib import import_module
from typing import Optional, Type

from ghostiss.container import Provider, Container, ABSTRACT

__all__ = [
    'Modules', 'ImportWrapper', 'DefaultModules', 'DefaultModulesProvider',
]


class Modules(ABC):

    @abstractmethod
    def import_module(self, modulename) -> ModuleType:
        """
        引用一个模块或抛出异常.
        :param modulename: 模块全路径.
        :exception: ModuleNotFoundError
        """
        pass


class ImportWrapper:
    def __init__(self, modules: Modules):
        self._modules = modules

    def __call__(self, modulename: str, globals_=None, locals_=None, from_list=None, level=-1):
        """
        可用于替换一个 module 上下文中的 __module__
        :param modulename: 完整的 module 路径.
        :param globals_: 默认不处理.
        :param locals_: 默认不处理.
        :param from_list: 应用的属性.
        :param level: 只能是 -1
        :return:
        """
        module = self._modules.import_module(modulename)
        result = []
        from_list = from_list if from_list is not None else []
        for name in from_list:
            if name in module.__dict__:
                result.append(module.__dict__[name])
            else:
                raise ModuleNotFoundError(f"Module {modulename} not found")
        return result


class DefaultModules(Modules):
    def import_module(self, modulename) -> ModuleType:
        return import_module(modulename)


class DefaultModulesProvider(Provider):
    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[ABSTRACT]:
        return Modules

    def factory(self, con: Container) -> Optional[ABSTRACT]:
        return DefaultModules()
