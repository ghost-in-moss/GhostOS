import inspect
from abc import ABC, abstractmethod
from typing import Optional, Type, Union, Iterable, Tuple
from types import ModuleType
from importlib import import_module, reload as reload_module
import pkgutil

from ghostos_container import Provider, Container

__all__ = [
    'Modules', 'ImportWrapper', 'DefaultModules', 'DefaultModulesProvider',
]


class Modules(ABC):

    @abstractmethod
    def import_module(self, modulename: str) -> ModuleType:
        """
        引用一个模块或抛出异常.
        :param modulename: 模块全路径.
        :exception: ModuleNotFoundError
        """
        pass

    @abstractmethod
    def getsource(self, modulename: str) -> str:
        """
        get source from a module.
        """
        pass

    @abstractmethod
    def save_source(self, modulename: str, source: str, reload: bool = False) -> None:
        """
        save source code to a module, and reload it.
        """
        pass

    @abstractmethod
    def iter_modules(self, module: Union[str, ModuleType]) -> Iterable[Tuple[str, bool]]:
        """
        like pkgutil.iter_modules.
        :return: Iterable[(module_name, is_package)].
        """
        pass

    @abstractmethod
    def reload(self, module: Union[str, ModuleType]):
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
    def import_module(self, modulename: str) -> ModuleType:
        return import_module(modulename)

    def getsource(self, modulename: str) -> str:
        module = self.import_module(modulename)
        source = inspect.getsource(module)
        return source

    def save_source(self, modulename: str, source: str, reload: bool = False) -> None:
        module = self.import_module(modulename)
        file = module.__file__
        with open(file, 'w') as f:
            f.write(source)
        if reload:
            self.reload(module)

    def iter_modules(self, module: Union[str, ModuleType]) -> Iterable[Tuple[str, bool]]:
        if isinstance(module, str):
            module_type = self.import_module(module)
        elif isinstance(module, ModuleType):
            module_type = module
        else:
            raise ValueError(f'Invalid module type: {type(module)}')
        prefix = module_type.__name__ + "."
        if not hasattr(module_type, "__path__"):
            return []
        path = module_type.__path__
        for i, name, is_pkg in pkgutil.iter_modules(path, prefix):
            yield name, is_pkg

    def reload(self, module: Union[str, ModuleType]):
        if isinstance(module, str):
            module = self.import_module(module)
        reload_module(module)


class DefaultModulesProvider(Provider[Modules]):
    def singleton(self) -> bool:
        return True

    def contract(self) -> Type:
        return Modules

    def factory(self, con: Container) -> Optional[Modules]:
        return DefaultModules()
