from typing import Optional

from ghostiss.framework.libraries.python_editor import PythonEditor, ModuleEditor
from ghostiss.core.moss_p1.exports import Exporter


class FakeModuleEditor(ModuleEditor):

    def folding_mode(self) -> str:
        return "folding_codes"

    def get_source(self, attr: Optional[str] = None, line_num: bool = False) -> str:
        return "get_source"

    def update(self, start: int, end: int, code: str) -> bool:
        return True

    def append(self, code: str) -> bool:
        return True


class FakePythonEditor(PythonEditor):

    def module(self, module: str, create: bool = False) -> Optional["ModuleEditor"]:
        return FakeModuleEditor()


EXPORTS = Exporter().attr('python_editor', FakePythonEditor(), PythonEditor)
