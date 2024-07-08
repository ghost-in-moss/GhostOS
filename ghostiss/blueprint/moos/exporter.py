from typing import Any, Optional, Callable, Dict, List, Type, TypedDict, Union, Set
from abc import ABC, abstractmethod
import inspect
from pydantic import BaseModel
from ghostiss.blueprint.moos.variable import Var, VarKind, ModelType
from ghostiss.container import Provider



class Variables:
    """
    在一个 module 内对外输出.
    """

    def __init__(self, export: bool = False):
        self._vars: Dict[str, Var] = {}
        self._orders: List[str] = []
        module = ""
        if export:
            module = get_caller_module(2)
        self._module: str = module

    def all(self) -> List[Var]:
        """
        返回所有的结果.
        """
        result = []
        for name in self._orders:
            result.append(self._vars[name])
        return result

    def var(
            self,
            name: str,
            val: Any,
            types: Optional[List[type]] = None,
            description: Optional[str] = None,
    ) -> "Variables":
        """
        声明一个变量, 直接添加到上下文中.

        :param name: 变量名.
        :param val: 变量的值.
        :param types: 定义这个变量时, 需要关联描述的类型.
        :param description: 变量的描述. 如果变量有 desc / description 字段, 或者是 DescribeAble 类型, 会自动获取.
        """

        self._check_duplicated_name(name)
        if types is None:
            # 添加一个声明的类型, 这个类型需要在上下文中展示.
            # built-in 类型的声明不需要强调.
            types = [type(val)]
        if description is None:
            description = get_description(val)
        v = Var(
            kind=VarKind.VALUE,
            value=val,
            name=name,
            description=description,
            module=self._module,
            module_val_name=name,
            types=types,
        )
        self._vars[name] = v
        return self

    def clazz(
            self,
            cls: type,
            alias: Optional[str] = None,
            types: Optional[List[type]] = None,
            description: Optional[str] = None,
            code_prompt: Optional[str] = None,
    ) -> "Variables":
        """
        声明一个类.
        :param cls: 一个类型. 默认只接受自定义类型.
        :param alias: 输出时对类名进行修改.
        :param types: 这个类需要连带输出的类.
        :param description: 关于类的描述, 默认使用类的 doc.
        :param code_prompt: 用人工定义的 prompt 替代这个类的 prompt.
        """
        if not inspect.isclass(cls):
            raise ValueError("cls must be a class")
        if issubclass(cls, BaseModel) or issubclass(cls, TypedDict):
            return self.model(cls, alias=alias, types=types, description=description, code_prompt=code_prompt)
        if alias is None:
            alias = cls.__name__
        self._check_duplicated_name(alias)

        if description is None:
            description = inspect.getdoc(cls)
        if types is None:
            types = []
        module = self._module
        module_val_name = alias
        if module is None:
            module = cls.__module__
            module_val_name = cls.__name__
        if code_prompt is None:
            code_prompt = get_class_prompt(cls)
        v = Var(
            kind=VarKind.CLASS,
            value=cls,
            name=alias,
            description=description,
            module=module,
            module_val_name=module_val_name,
            types=types,
            code_prompt=code_prompt,
        )
        self._vars[alias] = v
        return self

    def lib(
            self,
            ins: Any,
            alias: Optional[str] = None,
            types: Optional[List[type]] = None,
            description: Optional[str] = None,
            code_prompt: Optional[str] = None,
    ) -> "Variables":
        """
        输出一个类或者实例. 如果是类的话, 运行时会通过 container 获取它的实例.

        :param ins:
        :param alias:
        :param types:
        :param description:
        :param code_prompt:
        :return:
        """
        return self

    def caller(
            self,
            caller: Callable,
            alias: Optional[str] = None,
            types: Optional[List[type]] = None,
            description: Optional[str] = None,
            code_prompt: Optional[str] = None,
    ) -> "Variables":
        """
        输出一个 method 或者 function 作为上下文变量.
        它的 prompt 将是这个函数的 interface.
        :param caller:
        :param alias:
        :param types: 函数相关联, llm 需要理解的类型.
        :param description:
        :param code_prompt:
        :return:
        """
        if not inspect.isfunction(caller) and not inspect.ismethod(caller):
            raise ValueError("caller must be a function or method")
        name = alias
        if name is None:
            name = caller.__name__
        self._check_duplicated_name(name)

        if description is None:
            description = inspect.getdoc(caller)
        if code_prompt is None:
            code_prompt = get_callable_definition(caller, alias, description)
        module = self._module
        module_val_name = name
        if module is None:
            module = caller.__module__
            module_val_name = caller.__name__
        v = Var(
            kind=VarKind.CALLER,
            value=caller,
            name=name,
            description=description,
            module=module,
            module_val_name=module_val_name,
            types=None,
            code_prompt=code_prompt,
        )

        self._vars[name] = v
        return self

    def model(
            self,
            cls: Union[Type[BaseModel], Type[TypedDict]],
            alias: Optional[str] = None,
            types: Optional[List[type]] = None,
            description: Optional[str] = None,
            code_prompt: Optional[str] = None,
    ) -> "Variables":
        pass

    def provider(
            self,
            provider: Provider,
            alias: Optional[str] = None,
            description: Optional[str] = None,
            code_prompt: Optional[str] = None,
    ) -> "Variables":
        """
        将一个 provider 输出为一个变量.
        运行时将通过 provider.factory 方法动态从 container 中生成实例, 并且输出为 library 类型的变量.
        :param provider:
        :param alias:
        :param description:
        :param code_prompt:
        :return:
        """
        pass

    def _check_duplicated_name(self, name: str) -> None:
        if not name:
            raise ValueError("Variable name cannot be empty.")
        if name in self._vars:
            raise NameError(f"Duplicated variable name: {name}")
