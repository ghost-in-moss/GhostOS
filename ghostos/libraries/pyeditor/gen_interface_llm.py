from types import FunctionType
from typing import Dict, Union, Type, Optional
import inspect
from ghostos.libraries.pyeditor.abcd import PyInterfaceGenerator
from ghostos.contracts.modules import Modules
from ghostos.contracts.workspace import Workspace
from ghostos.core.llms import LLMs, Prompt, LLMApi
from ghostos.core.messages import Role
from ghostos_common.helpers import md5, import_from_path, generate_import_path, yaml_pretty_dump
from ghostos_container import Container, Provider, INSTANCE
from pydantic import BaseModel, Field
import yaml

__all__ = ['LLMPyInterfaceGeneratorImpl', 'LLMPyInterfaceGeneratorProvider']


class InterfaceCache(BaseModel):
    data: Dict[str, str] = Field(default_factory=dict, description="from code hash to the interface")


def function_parse_instruction(import_path: str, source_code: str) -> str:
    return f"""
Your request is to generate interface code of a function.

the `function interface` include: 
1. the function definition, such as `def func_name(arg1: type_hint, arg2: type_hint) -> return_type_hint:`
2. the function's docstring, but make it simple and clear. 
3. use nature language comments to replace the function body code, just describe the steps of the function body in very simple words.
4. add `pass` to the end of the body. 

for example, a function is: 

```python
def sqrt_newton(n, epsilon=1e-7):
    '''
    使用牛顿迭代法计算平方根
    :param n: 要计算平方根的数
    :param epsilon: 迭代精度
    :return: 平方根的近似值
    '''
    if n < 0:
        raise ValueError("Cannot compute square root of a negative number")
    x = n
    while abs(x * x - n) > epsilon:
        x = (x + n / x) / 2
    return x
```

the interface of it shall be:

```python
def sqrt_newton(n: float, epsilon=1e-7) -> float:
    '''
    使用牛顿迭代法计算平方根
    :param n: 要计算平方根的数
    :param epsilon: 迭代精度
    :return: 平方根的近似值
    '''
    # 1. validate the n is positive
    # 2. use newton sqrt to compute the square root in the loop until it is less than epsilon
    pass
```

and you shall do better than this. 

the function you are parsing is `{import_path}`, the source code of it is: 

```python
{source_code}
```

NOTICES:
1. YOU ARE REQUIRED TO GENERATE THE INTERFACE CODE ONLY, embrace it with '```python' and '```'. 
2. So your reply shall start with '```python' and end with '```', nothing more.
3. If the source code is not a valid python function, you shall directly return `no`  .

now generate the interface code:
"""


def class_parse_instruction(import_path: str, source_code: str) -> str:
    return f"""
Your request is to generate interface code of a class.

The `class interface` is for the user of the class to understand how to use it.
The user usually care about interface only instead of the source code.

the `class interface` include: 
1. the class definition, such as `class ClassName(parent_classes):`
2. the class's docstring, but make it simple and clear. 
3. the interfaces of the public methods of it. the interfaces means only definition and docstring are required, the method body shall be replaced with `pass`.
    * the `public methods` means the method name shall not start with `_` 
4. the public attributes of it, with the typehint and docstring of the attributes.
5. add more information about the usage of the class, if they are missing.

considering your generated interface code shall be informative to the user who wants to use the class. 

the class you are parsing is `{import_path}`, the source code of it is: 

```python
{source_code}
```

NOTICES:
1. YOU ARE REQUIRED TO GENERATE THE INTERFACE CODE ONLY, embrace it with '```python' and '```'. 
2. So your reply shall start with '```python' and end with '```', nothing more.
3. If the source code is not a valid python function, you shall return the reason start with `no:`  .

now generate the interface code:
"""


class LLMPyInterfaceGeneratorImpl(PyInterfaceGenerator):
    """
    simple implementation of PyInterfaceGenerator
    """

    def __init__(
            self, *,
            workspace: Workspace,
            modules: Modules,
            llms: LLMs,
            llm_api: str = "",
            filename: str = "pyinterface_cache.yml",
    ):
        self._storage = workspace.runtime_cache()
        self._modules = modules
        self._llms = llms
        self._llm_api = llm_api
        self._filename = filename
        self._interface_cache: InterfaceCache = self._get_interface_cache()

    def _get_interface_cache(self) -> InterfaceCache:
        if self._storage.exists(self._filename):
            content = self._storage.get(self._filename)
            data = yaml.safe_load(content)
            cache = InterfaceCache(**data)
        else:
            cache = InterfaceCache()
        return cache

    def generate_interface(self, value: Union[FunctionType, Type, str], llm_api: str = "",
                           cache: bool = True) -> str:
        is_class = inspect.isclass(value)
        if is_class or inspect.isfunction(value):
            source = inspect.getsource(value)
            import_path = generate_import_path(value)
        elif isinstance(value, str):
            import_path = value
            value = import_from_path(import_path, self._modules.import_module)
            source = inspect.getsource(value)
            is_class = inspect.isclass(value)
        else:
            raise AttributeError(f"Cannot generate interface for {type(value)}")

        return self._generate_interface_from_source(source, import_path, is_class, llm_api, cache)

    def _generate_interface_from_source(self, source_code: str, import_path: str, is_class: bool, llm_api: str,
                                        cache: bool = True) -> str:
        hash_ = md5(source_code)
        if cache and hash_ in self._interface_cache:
            return self._interface_cache[hash_]

        if is_class:
            instruction = class_parse_instruction(import_path, source_code)
        else:
            instruction = function_parse_instruction(import_path, source_code)

        interface_code = self._generate_interface_by_llm(instruction, import_path, llm_api)
        if interface_code:
            self._interface_cache.data[hash_] = interface_code
            self._save_cache()
        return interface_code

    def _save_cache(self):
        data = self._interface_cache.model_dump(exclude_defaults=True)
        content = yaml_pretty_dump(data)
        self._storage.put(self._filename, content.encode())

    def _generate_interface_by_llm(self, instruction: str, import_path: str, llm_api: str) -> str:
        prompt = Prompt(
            system=[Role.SYSTEM.new(content=instruction)],
        )
        api = self._get_llm_api(llm_api)
        message = api.chat_completion(prompt)
        content = message.get_content()
        if content.startswith('no:'):
            raise AttributeError(f"Cannot generate interface for `{import_path}`")

        parts = content.split('```python')
        if len(parts) > 1:
            content = "".join(parts[1:])
            parts = content.split('```')
            content = parts[0]

        return content.strip('```python').strip('```').strip()

    def _get_llm_api(self, llm_api: str) -> LLMApi:
        if not llm_api:
            llm_api = self._llm_api
        return self._llms.get_api(llm_api)


class LLMPyInterfaceGeneratorProvider(Provider[PyInterfaceGenerator]):

    def __init__(self, llm_api: str = ""):
        self._llm_api = llm_api

    def singleton(self) -> bool:
        return True

    def factory(self, con: Container) -> Optional[INSTANCE]:
        ws = con.force_fetch(Workspace)
        modules = con.force_fetch(Modules)
        llms = con.force_fetch(LLMs)

        return LLMPyInterfaceGeneratorImpl(
            workspace=ws,
            modules=modules,
            llms=llms,
            llm_api=self._llm_api,
        )
