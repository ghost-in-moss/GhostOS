from typing import Optional

from ghostos_moss.abcd import SelfUpdater
from ghostos_moss.modules import Modules
from ghostos_moss.pycontext import PyContext
from ghostos_common.helpers import get_attr_source_from_code
from ghostos_container import Container, Provider
import inspect
import os

__all__ = ["SelfUpdaterImpl", "SelfUpdaterProvider"]


class SelfUpdaterImpl(SelfUpdater):

    def __init__(self, pycontext: PyContext, modules: Modules):
        self.pycontext = pycontext
        self.modules = modules

    def append(self, code: str) -> None:
        source = self.getsource()
        new_code = "\n\n".join([source.rstrip(""), code.rstrip()]) + "\n"
        self.rewrite(new_code)

    def replace_attr(self, attr_name: str, code: str) -> None:
        source = self.getsource()
        origin = get_attr_source_from_code(source).get(attr_name, None)
        if origin:
            source = source.replace(origin, code, 1)
            self.rewrite(source)

    def getsource(self) -> str:
        if self.pycontext.code:
            return self.pycontext.code
        if self.pycontext.module:
            module = self.modules.import_module(self.pycontext.module)
            return inspect.getsource(module)
        return ""

    def rewrite(self, code: str) -> None:
        self.pycontext.code = code

    def save(self, reload: bool = True) -> None:
        if not self.pycontext.module:
            return None
        module = self.modules.import_module(self.pycontext.module)
        filename = module.__file__
        if os.path.exists(filename):
            with open(filename, "w") as f:
                f.write(self.pycontext.code)
            if reload:
                self.modules.reload(module)


class SelfUpdaterProvider(Provider[SelfUpdater]):

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[SelfUpdater]:
        pycontext = con.force_fetch(PyContext)
        modules = con.force_fetch(Modules)
        return SelfUpdaterImpl(pycontext, modules)
