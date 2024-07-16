from abc import ABC, abstractmethod
import importlib
from typing import Optional, Type

from ghostiss.core.moss.reflect import reflect, Reflection
from ghostiss.core.moss.exports import EXPORTS_KEY, Exports
from ghostiss.container import Provider, Container, CONTRACT


class Modules(ABC):

    @abstractmethod
    def imports(self, module: str, spec: str) -> Reflection:
        """
        引入一个库.
        todo: 实现 storage based modules. 进行前缀匹配, 可以将agent 的 workspace 目录变成临时的 import 路径.
        """
        pass


class BasicModules(Modules):

    def imports(self, module: str, spec: str) -> Reflection:
        module_ins = self._imports(module)
        if EXPORTS_KEY in module_ins:
            # use EXPORTS instead of the module
            exports = module_ins[EXPORTS_KEY]
            if isinstance(exports, Exports):
                return exports.get(spec)

        if spec in module_ins:
            spec_value = module_ins[spec]
            ref = reflect(var=spec_value)
            ref.update(module=module, module_spec=spec)
            return ref
        raise ModuleNotFoundError(f"spec {spec} not found in {module}")

    def _imports(self, module: str):
        return importlib.import_module(module)


class BasicModulesProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[CONTRACT]:
        return Modules

    def factory(self, con: Container) -> Optional[CONTRACT]:
        return BasicModules()
