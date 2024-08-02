from abc import ABC, abstractmethod
from typing import Optional
from ghostiss.core.moss.exports import Exporter


class PythonEditor(ABC):
    """
    You are equipped with this Editor that useful to edit certain python module's code.
    Only certain modules can be edited, others will throw an NotImplementedError.
    """

    @abstractmethod
    def module(self, module: str, create: bool = False) -> Optional["ModuleEditor"]:
        """
        use module name to new an ModuleEditor instance.
        :param module: module name such as foo.bar
        :param create: create new module if module not exists
        """
        pass


class ModuleEditor(ABC):
    """
    Python Module Editor that useful to edit the module's code.
    Notice you can write code in string, and use the ModuleEditor's api to update real python code file.
    """

    @abstractmethod
    def folding_mode(self) -> str:
        """
        :return: show the module's code in folding mode with signature and docs only.
        """

    @abstractmethod
    def get_source(self, attr: Optional[str] = None, line_num: bool = False) -> str:
        """
        get source code of the module or module's attr.
        :param attr: if given, get the source code of it values
        :param line_num: if True, each line will end with line number comment such as # 1
        """
        pass

    @abstractmethod
    def update(self, start: int, end: int, code: str) -> bool:
        """
        replace the module's code block with new code, and update the code file.
        :param start: replacing block's start line num
        :param end: replacing block's end line num
        :param code: new code, if empty then remove the block only.
        :return: success
        """
        pass

    @abstractmethod
    def append(self, code: str) -> bool:
        """
        append new code to the module, and update the code file.
        :param code: new code
        :return: success
        """
        pass


EXPORTS = Exporter().interface(PythonEditor).interface(ModuleEditor)
