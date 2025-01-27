from typing import List, Iterable, Union, Type
from typing_extensions import Literal
from types import FunctionType
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field

__all__ = [
    'PyInspector',
    'PyInterfaceGenerator',
    'PyModuleEditor',
    'LocalPyMI',
]


class PyInspector(ABC):
    """
    这个工具可以自动展示你关心的 python 对象信息.
    将它绑定到 Moss 上, 你可以自动看到这些对象的相关讯息.

    当你想添加想要关注的对象时, 只要把它的 import_path 添加到相关属性即可.
    注意当其中一些对象你不需要再关注时, 请通过数组操作主动去掉它们.
    """

    _IMPORT_PATH = str
    """str pattern [module_name] or [module_name:attr_name]. such as `inspect:get_source`"""

    reading_source: List[_IMPORT_PATH]
    """你正在关注, 需要展示源代码的对象."""

    reading_interface: List[_IMPORT_PATH]
    """你正在关注, 需要展示 interface 信息的对象. interface 只包含调用者关心的讯息"""

    @abstractmethod
    def get_source(self, import_path: str) -> str:
        """
        get the source of the target.
        :return: the source code of the target
        """
        pass

    @abstractmethod
    def get_brief(self, import_path: str) -> str:
        """
        get the brief of the target.
        """
        pass

    @abstractmethod
    def get_interface(self, import_path: str) -> str:
        """
        get the interface of the target.
        """
        pass

    @abstractmethod
    def dump_inspecting(self) -> str:
        """
        :return: the inspecting information
        """
        pass


class PyModuleEditor(ABC):
    """
    can edit python module
    """

    modulename: str
    """the editing module name"""

    filename: str
    """the absolute filename of the module"""

    @classmethod
    @abstractmethod
    def new(cls, module_name: str) -> "PyModuleEditor":
        """
        generate a new PyModuleEditor
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
        :param show_line_num: if true, each line start with `[number]| `, don't confuse them with the code.
        :param start_line: start line number
        :param end_line: end line number, if < 0, means end line number
        :return: source code
        """
        pass

    @abstractmethod
    def get_source_block(
            self,
            start_with: str,
            end_with: str,
    ) -> str:
        """
        get first block that match the start and end lines.
        useful when you want to get the block of the module source code, and replace them later.
        :param start_with: target block start chars.
        :param end_with: target block end chars.
        :return: the origin string
        """
        pass

    @abstractmethod
    def replace(
            self,
            target_str: str,
            replace_str: str,
            count: int = -1
    ) -> bool:
        """
        replace the source code of this module by replace a specific string
        :param target_str: target string in the source code
        :param replace_str: replacement
        :param count: if -1, replace all occurrences of replace_str, else only replace occurrences count times.
        :return: if not ok, means target string is missing
        """
        pass

    @abstractmethod
    def append(self, source: str) -> None:
        """
        append source code to this module.
        :param source: the source code of class / function / assignment
        """
        pass

    @abstractmethod
    def insert(self, source: str, line_num: int) -> None:
        """
        insert source code to this module at line number.
        remember following the python code format pattern.
        :param source: the inserting code, such like from ... import ... or others.
        :param line_num: the start line of the insertion
        """
        pass

    @abstractmethod
    def replace_attr(
            self,
            attr_name: str,
            replace_str: str,
    ) -> str:
        """
        replace a module attribute's source code.
        the target attribute shall be a class or a function.
        :param attr_name: name of the target attribute of this module.
        :param replace_str: new source code
        :return: the replaced source code. if empty, means target attribute is missing
        """
        pass


# ---- local pymi ---- #

class ModuleAPI(BaseModel):
    """
    the module attribute information
    """
    name: str = Field(description="the name of the attribute in the module")
    type: Literal["function", "class"] = Field(description="the type of the attribute, usually `class` or `function`")
    description: str = Field(description="the description of the attribute")
    interface: str = Field(
        description="the interface of the attribute to whom want to use this attribute."
                    "the interface of a function shall be definition and it's arguments/returns typehint, and doc."
                    "the interface of a class shall be definition, public methods, public attributes, __init__. "
    )


class ModuleInfo(BaseModel):
    name: str = Field(description="the module name")
    description: str = Field(default="", description="the module description, in 100 words")
    readme: str = Field(default="", description="the basic usage of the module")
    keywords: List[str] = Field(default_factory=list, description="the keywords of the module")
    exports: List[ModuleAPI] = Field(
        default_factory=list,
        description="the api that useful to the user of the module"
    )
    recall_corpus: List[str] = Field(
        default_factory=list,
        description="the sentences that you may use to recall the module, "
                    "system may use them to calculate the similarity from the query"
    )
    hash: str = Field(description="the content hash of the module.")


class LocalPyMI(ABC):
    """
    local python module index.
    A manager that can recall local python module or attributes.

    useful when:
    1. you want to check a library is installed, use `exists` method.
    2. some local python module, function, and classes are unknown to you, you may need to search them.
    """

    @abstractmethod
    def save_module_info(self, module_info: ModuleInfo) -> None:
        """
        save the module information to the index.
        :param module_info: the module info
        """
        pass

    @abstractmethod
    def exists(self, import_path: str) -> bool:
        """
        check the existence of an expecting module or module attribute.
        :param import_path: [modulename:attr_name]
        """
        pass

    @abstractmethod
    def search(
            self,
            expectation: str,
            query: str,
            top_n: int = 10,
    ) -> Iterable[ModuleInfo]:
        """
        search the saved module info.
        :param expectation:
        :param query:
        :param top_n:
        :return:
        """
        pass


class PyInterfaceGenerator(ABC):
    """
    generate an interface string of the python function or class
    """

    @abstractmethod
    def generate_interface(
            self,
            class_or_function: Union[FunctionType, Type, str],
            llm_api: str = "",
            cache: bool = True,
    ) -> str:
        """
        :param class_or_function: class, function, or it's import path (in pattern [modulename:attr_name])
        :param llm_api: the llm api name, see ghostos.core.llms.LLMsConf
        :param cache: read from cache first
        """
        pass
