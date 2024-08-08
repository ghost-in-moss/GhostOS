from abc import ABC, abstractmethod
import importlib
from types import ModuleType
from typing import Optional, Type

from ghostiss.core.moss_p1.reflect import reflect, reflects, Reflection, Importing
from ghostiss.core.moss_p1.exports import EXPORTS_KEY, Exporter
from ghostiss.container import Provider, Container, ABSTRACT


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
        if spec == '*':
            if exports:
                return exports
            else:
                __all__ = {}
                if '__all__' in module_ins.__dict__:
                    for key in module_ins.__dict__['__all__']:
                        __all__[key] = module_ins.__dict__[key]
                else:
                    __all__ = module_ins.__dict__
                return Exporter(with_module=False, deep_copy=False).reflects(**__all__)
        if spec is None:
            # 将整个 module 返回.
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

    def contract(self) -> Type[ABSTRACT]:
        return Modules

    def factory(self, con: Container) -> Optional[ABSTRACT]:
        return BasicModules()
