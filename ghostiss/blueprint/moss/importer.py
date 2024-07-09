from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field
from ghostiss.blueprint.moss.variable import Var

#
# class Index(BaseModel):
#     module: str
#     value: Optional[str] = Field(default=None)
#     description: Optional[str] = Field(default="")
#     embeddings: Dict[str, List[float]] = Field(default_factory=dict)
#
#
# class Imported:
#
#     def __init__(
#             self,
#             *,
#             value: Any,
#             module: str,
#             module_value: Optional[str] = None,
#             description: Optional[str] = None,
#             prompt: Optional[str] = None,
#     ):
#         self.value = value
#         self.module = module
#         self.module_value = module_value
#         self.description = description
#         self.prompt = prompt
#
#
# class Module(BaseModel):
#     """
#     对模块的描述.
#     """
#     parent: Optional[str]
#     module: str
#     description: str
#     embeddings: Dict[str, List[float]] = Field(default_factory=dict)
#
#
# class ModuleValue(BaseModel):
#     """
#     对模块里的值的描述.
#     """
#     module: str
#     value_name: str
#     description: str
#     embeddings: Dict[str, List[float]] = Field(default_factory=dict)


class Importer(ABC):

    @abstractmethod
    def imports(self, module: str, spec: str) -> Var:
        """
        引入一个库.
        """
        pass
    #
    # @abstractmethod
    # def search_module(self, desc: str, limit: int = 10) -> List[Module]:
    #     """
    #     搜索已经加载的模块.
    #     """
    #     pass
    #
    # @abstractmethod
    # def install_module(self, module_prefix: str) -> List[Module]:
    #     """
    #     加载一个目录下的所有模块.
    #     """
    #     pass
    #
    # @abstractmethod
    # def search_package(self, description: str) -> str:
    #     """
    #     搜索包.
    #     """
    #     pass
    #
    # @abstractmethod
    # def get_source(self, module: str, module_value: Optional[str] = None) -> str:
    #     """
    #     返回一个位置的源码.
    #     """
    #     pass
    #
    # @abstractmethod
    # def get_prompt(self, value: Any) -> str:
    #     """
    #     描述一个数据.
    #     """
    #     pass
