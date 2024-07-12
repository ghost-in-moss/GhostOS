from abc import ABC, abstractmethod
import importlib
from typing import Optional, Type

from ghostiss.blueprint.moss.reflect import reflect, Reflection
from ghostiss.container import Provider, Container, CONTRACT


class Modules(ABC):

    @abstractmethod
    def imports(self, module: str, spec: str) -> Reflection:
        """
        引入一个库.
        """
        pass


class BasicModules(Modules):

    def imports(self, module: str, spec: str) -> Reflection:
        module_ins = importlib.import_module(module)
        if spec in module_ins:
            spec_value = module_ins[spec]
            ref = reflect(var=spec_value)
            ref.update(module=module, module_spec=spec)
            return ref
        raise ModuleNotFoundError(f"spec {spec} not found in {module}")


class BasicModulesProvider(Provider):

    def singleton(self) -> bool:
        return True

    def contract(self) -> Type[CONTRACT]:
        return Modules

    def factory(self, con: Container) -> Optional[CONTRACT]:
        return BasicModules()
