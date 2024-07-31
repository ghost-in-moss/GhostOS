from abc import ABC, abstractmethod
import importlib
from types import ModuleType
from typing import Optional, Type

from ghostiss.core.moss.reflect import reflect, Reflection, Importing
from ghostiss.core.moss.exports import EXPORTS_KEY, Exporter
from ghostiss.container import Provider, Container, CONTRACT


class Modules(ABC):

    # @abstractmethod
    # def import_any(
    #         self,
    #         module: str,
    #         global_values: Optional[Dict] = None,
    #         local_values: Optional[Dict] = None,
    #         fromlist: Optional[List] = None,
    #         level: int = 0,
    # ) -> List[Any]:
    #     """ 暂时先不实现, 主要解决 module 互相调用 """
    #     pass

    @abstractmethod
    def imports(self, module: str, spec: Optional[str] = None) -> Reflection:
        """
        引入一个库.
        todo: 实现 storage based modules. 进行前缀匹配, 可以将agent 的 workspace 目录变成临时的 import 路径.
        """
        pass

    @abstractmethod
    def destroy(self) -> None:
        pass


class BasicModules(Modules):

    def imports(self, module: str, spec: Optional[str] = None) -> Reflection:
        module_ins = self._imports(module)
        exports = None
        if EXPORTS_KEY in module_ins.__dict__:
            # use EXPORTS instead of the module
            exports = module_ins.__dict__[EXPORTS_KEY]
        if spec is None:
            if exports:
                return exports
            else:
                return Importing(value=module_ins, module=module, module_spec=spec)

        if isinstance(exports, Exporter):
            return exports.get(spec)
        if spec in module_ins.__dict__:
            spec_value = module_ins.__dict__[spec]
            if spec_value is None:
                raise ModuleNotFoundError(f"{spec} is not defined in module {module}")
            ref = reflect(var=spec_value, name=spec)
            if ref:
                ref.update(module=module, module_spec=spec)
            return ref
        raise ModuleNotFoundError(f"spec {spec} not found in {module}")

    def _imports(self, module: str) -> ModuleType:
        return importlib.import_module(module)

    def destroy(self) -> None:
        return None


class BasicModulesProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[CONTRACT]:
        return Modules

    def factory(self, con: Container) -> Optional[CONTRACT]:
        return BasicModules()
