from typing import List, Optional, Any
from typing_extensions import Self
from abc import ABC, abstractmethod
from ghostos_common.prompter import POM

__all__ = [
    'PyInspector',
    'PyInterfaceGenerator',
    'PyModuleEditor',
    'PyMI',
]


class PyInspector(POM, ABC):
    """
    这个工具可以自动展示你关心的 python 对象信息.
    作为一个 PromptObjectModel, 如果将它绑定到 Moss 上, 你可以自动看到这些对象的相关讯息, 并且可以在多轮对话中保存.

    当你想添加想要关注的对象时, 只要把它的 import_path 添加到相关属性即可.
    注意当其中一些对象你不需要再关注, 或者不需要关注你也能看到信息时, 请通过数组操作主动去掉它们, 避免 token 浪费.
    """

    _IMPORT_PATH = str
    """str pattern [module_name] or [module_name:attr_name]. such as `inspect:get_source`"""

    watching_source: List[_IMPORT_PATH]
    """你正在关注, 需要展示源代码的对象. 可以添加或删除这些关注对象. """

    watching_interface: List[_IMPORT_PATH]
    """你正在关注, 需要展示 interface 信息的对象. interface 只包含调用者关心的讯息. 可以添加或删除这些信息. """

    @abstractmethod
    def get_source(self, import_path: _IMPORT_PATH) -> str:
        """
        get the source of the target.
        调用这个方法就不需要 watching.
        :return: the source code of the target
        """
        pass

    @abstractmethod
    def get_interface(self, import_path: _IMPORT_PATH) -> str:
        """
        get the interface of the target.
        `interface` here means definition of the function or class, exclude code body of function or method.
        调用这个方法就不需要 watching.
        """
        pass

    @abstractmethod
    def dump_context(self) -> str:
        """
        :return: the inspecting information
        """
        pass


# ---- local pymi ---- #

class PyModuleEditor(ABC):
    """
    can edit python module
    """

    modulename: str
    """the editing module name"""

    filename: str
    """the absolute filename of the module"""

    @abstractmethod
    def new_from(self, modulename: str) -> Self:
        """
        create new module editor
        """
        pass

    @abstractmethod
    def get_source(
            self,
            show_line_num: bool = False,
            start_line: int = 0,
            end_line: int = -1,
    ) -> str:
        """
        read source code from this module
        :param show_line_num: if true, each line start with `[number]|`, for example:
                source code: `def foo():`
                show line number: ` 1|def foo():`.
               don't confuse the prefix line num is the part of the file.
        :param start_line: start line number
        :param end_line: end line number, if < 0, means end line number
        :return: source code
        """
        pass

    @abstractmethod
    def get_imported_attrs_interfaces(self) -> str:
        """
        get imported attrs source code interfaces (definitions and signatures)
        convenient way to use imported attrs without read source code from them.
        """
        pass

    @abstractmethod
    def replace(
            self,
            target_str: str,
            replace_str: str,
            count: int = 1,
            reload: bool = False,
    ) -> bool:
        """
        replace the source code of this module by replace a specific string
        :param target_str: target string in the source code
        :param replace_str: replacement
        :param count: if -1, replace all occurrences of replace_str, else only replace occurrences count times.
        :param reload: if False, update but note save to the module.
        :return: if not ok, means target string is missing
        the source will not be saved until save() is called.
        """
        pass

    @abstractmethod
    def append(self, source: str, reload: bool = False) -> None:
        """
        append source code to this module.
        :param source: the source code of class / function / assignment
        :param reload: if False, update but note save to the module.
        """
        pass

    @abstractmethod
    def insert(self, source: str, line_num: int, reload: bool = False) -> None:
        """
        insert source code to this module at line number.
        remember following the python code format pattern.
        :param source: the inserting code, such like from ... import ... or others.
        :param line_num: the start line of the insertion. if 0, insert to the top. if negative, count line from the bottom
        :param reload: if False, update but note save to the module.
        the source will not be saved until save() is called.
        """
        pass

    @abstractmethod
    def replace_attr(
            self,
            attr_name: str,
            replace_str: str,
            reload: bool = False,
    ) -> str:
        """
        replace a module attribute's source code.
        the target attribute shall be a class or a function.
        :param attr_name: name of the target attribute of this module.
        :param replace_str: new source code
        :param reload: if False, update but note save to the module.
        :return: the replaced source code. if empty, means target attribute is missing
        """
        pass

    @abstractmethod
    def save(self, reload: bool = True, source: Optional[str] = None) -> None:
        """
        save the module changes to file.
        otherwise only the editor's cached source code will be changed.
        :param reload: if True, reload the module from the saved source code.
        :param source: if the source given, replace all the source code.
        """
        pass


class PyMI(ABC):
    """
    local python module index.
    todo: recall modules.
    """

    @abstractmethod
    def save_module(self, modulename: str, code: str) -> None:
        """
        save module with source code
        :param modulename: the name of the module
        :param code: the source code
        """
        pass

    @abstractmethod
    def new_module_editor(self, modulename: str) -> PyModuleEditor:
        """
        new a python module editor to modify the source code of the module.
        """
        pass

    @abstractmethod
    def exists(self, import_path: str) -> bool:
        """
        check the existence of an expecting module or module attribute.
        :param import_path: [modulename:attr_name]
        """
        pass


class PyInterfaceGenerator(ABC):
    """
    generate an interface string of the python function or class
    """

    @abstractmethod
    def generate_interface(
            self,
            value: Any,
    ) -> str:
        """
        :param value: class, function, or it's import path (in pattern [modulename:attr_name])
        """
        pass
