from typing import List, Any, Optional, Dict, Type
import re
import inspect
from abc import ABC, abstractmethod
from pydantic import BaseModel
from ghostiss.blueprint.moos.context import PyContext, PyLocals, Define, VARIABLE_TYPES
from ghostiss.blueprint.moos.importer import Importer
from ghostiss.blueprint.messages.message import Message




class PyRuntime(ABC):
    @abstractmethod
    def vars(self) -> Dict[str, Var]:
        pass

    @abstractmethod
    def locals(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def prompt(self) -> str:
        pass

    @abstractmethod
    def context(self) -> PyContext:
        """
        返回当前的 PyContext.
        """
        pass

    @abstractmethod
    def append_messages(self, *messages: Message) -> None:
        """
        插入消息.
        """
        pass

    @abstractmethod
    def imports(self, module: str, *values: str, **alias: Dict[str, str]):
        """

        """
        pass

    @abstractmethod
    def define(self, name: str, value: VARIABLE_TYPES, desc: Optional[str] = None, model: Optional[str] = None) -> Any:
        """
        定义一个变量.
        """
        pass

    @abstractmethod
    def delete(self, var_name: str) -> None:
        """
        删除一个变量.
        """
        pass

    @abstractmethod
    def messages(self) -> List[Message]:
        """
        运行过程中产生的消息体.
        """
        pass


class BasicPyRuntime(PyRuntime):

    def __init__(self, ctx: "PyContext", local: "PyLocals", importer: Importer):
        self._ctx = ctx.model_copy()
        self._importer = importer
        self._locals = local
        self._messages: List[Message] = []

    def vars(self) -> Dict[str, Var]:
        """
        当前上下文中存在的变量.
        """
        variables: Dict[str, Var] = {}
        self._add_local_variables(variables)
        self._add_ctx_variables(variables)

    def _add_local_variables(self, variables: Dict[str, Var]) -> None:
        pass

    def _add_ctx_variables(self, variables: Dict[str, Var]) -> None:
        # 添加 importing.
        for importing in self._ctx.imports:
            imported = self._importer.imports(importing.module, importing.value)
            v = Var(
                name=importing.get_name(),
                value=imported.value,
                description=imported.description,
                prompt=imported.prompt,
                module=imported.module,
                module_value=imported.module_value,
            )
            self._add_var(variables, v)

        for ctx_value in self._ctx.defines:
            if ctx_value.model is not None:
                model = self._get_model(ctx_value.model)
                value = model(**ctx_value.value)
            else:
                value = ctx_value.value
            v = Var(
                name=ctx_value.get_name(),
                value=value,
                description=ctx_value.get_description(),
            )
            self._add_var(variables, v)

    def _add_var(self, variables: Dict[str, Var], add: Var) -> None:
        name = add.name
        if name not in variables.items():
            variables[name] = add.value
            return
        matched = re.search(r"__%d$", name)
        if matched is None:
            name = name + "__1"
            add.name = name
            self._add_var(variables, add)
            return
        suffix = name[matched.pos: matched.endpos]
        suffix_num = int(suffix.lstrip("__"))
        num = suffix_num + 1
        name = name[:matched.pos] + f"__{num}"
        add.name = name
        self._add_var(variables, add)

    def _get_model(self, model: str) -> Optional[Type[BaseModel]]:
        pass

    def define(self, name: str, value: VARIABLE_TYPES, desc: Optional[str] = None, model: Optional[str] = None) -> Any:
        v = Define(name=name, value=value, description=desc, model=model)
        self._ctx.add_var(v)
        return v.value
