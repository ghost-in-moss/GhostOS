from typing import Optional
from ghostos.libraries.pyeditor import PyModuleEditor
from ghostos.libraries.pyeditor.abcd import LocalPyMI
from ghostos.libraries.pyeditor.simple_module_editor import SimplePyModuleEditor
from ghostos.contracts.modules import Modules, DefaultModules
from ghostos.helpers import import_from_path
from ghostos.container import Container, Provider

__all__ = ['SimpleLocalPyMIProvider', 'SimplePyMI']


class SimplePyMI(LocalPyMI):

    def __init__(self, modules: Optional[Modules] = None):
        self._modules = modules if modules is not None else DefaultModules()

    def save_module(self, modulename: str, code: str) -> None:
        editor = SimplePyModuleEditor(modulename, modules=self._modules)
        editor.save(source=code)

    def new_module_editor(self, modulename: str) -> PyModuleEditor:
        return SimplePyModuleEditor(modulename, modules=self._modules)

    def exists(self, import_path: str) -> bool:
        try:
            _ = import_from_path(import_path, self._modules.import_module)
            return True
        except ImportError:
            return False


class SimpleLocalPyMIProvider(Provider[LocalPyMI]):

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[LocalPyMI]:
        modules = con.get(Modules)
        return SimplePyMI(modules)
