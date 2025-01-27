from typing import List
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class PyInspector(ABC):
    """
    inspect the briefs or source code of the watching targets,
    and automatically provide the information for you.
    """

    class TypeBrief(BaseModel):
        """
        the brief of the inspected type
        """
        import_path: str = Field(description="Import path in the pattern [module_name:type_name]")
        type: str = Field(description="the type of the object")
        signature: str = Field(description="the signature of the type object, include name, doc, arguments")

    class Watching(BaseModel):
        read_source: List[str] = Field(
            default_factory=list,
            description="the import path list that ",
        )

    watching: Watching
    """
    the watching targets.
    """

    @abstractmethod
    def get_source(self, import_path: str) -> str:
        """
        get the source of the target.
        :param import_path: str pattern [module_name] or [module_name:attr_name]. such as `inspect:get_source`
        :return: the source code of the target
        :exception: ModuleNotFoundError, ImportError
        """
        pass

    @abstractmethod
    def get_brief(self, import_path: str) -> str:
        """
        get the brief of the target.
        :param import_path: str pattern [module_name] or [module_name:attr_name]. such as `inspect:get_source`
        :return: the brief about import_path/type/signature/doc of the target
        :exception: ModuleNotFoundError, ImportError
        """
        pass

    @abstractmethod
    def get_interface(self, import_path: str) -> str:
        """
        get the interface of the target.
        when you want to use
        :param import_path:
        :return:
        """


class PyModuleEditor(ABC):
    """
    can edit python module
    """

    module_name: str
    """
    the editing module name
    """
