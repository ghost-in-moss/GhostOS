from typing import Callable, Optional, Dict, List, Any, Tuple
import os
import yaml
import importlib

from ghostos_container import Container
from ghostos.core.runtime import GoThreadInfo, EventTypes, thread_to_prompt
from ghostos_moss import MossRuntime, MossCompiler, PyContext
from ghostos.core.llms import LLMs, LLMApi
from ghostos.core.messages import Role, Message
from ghostos_common.helpers import yaml_pretty_dump
from pydantic import BaseModel, Field

__all__ = ["GhostFuncDriver", "GhostFuncCache", 'get_ghost_func_cache', 'save_ghost_func_cache']

DECORATOR = Callable[[Callable], Callable]


class GhostFuncCache(BaseModel):
    """
    the ghost func cache that follows a python file
    """
    modulename: str = Field(description="the module name that decorated function located")
    filename: Optional[str] = Field(default=None, description="the filename that decorated function located")
    threads: Dict[str, GoThreadInfo] = Field(
        default_factory=dict,
        description="a map of function.__qualname__ to thread instance",
    )


def get_ghost_func_cache(modulename: str, filename: Optional[str] = None) -> GhostFuncCache:
    """
    get ghost func from file or create one
    """
    if not os.path.exists(filename):
        return GhostFuncCache(modulename=modulename, filename=filename)
    with open(filename, "rb") as f:
        content = f.read()
        data = yaml.safe_load(content)
        return GhostFuncCache(**data)


def save_ghost_func_cache(cache: GhostFuncCache, importer: Optional[Callable] = None) -> None:
    """
    save ghost func cache to file.
    if filename not given, filename would be the module.__file__ - '.py' + 'ghost_funcs.yml'
    """
    filename = cache.filename
    if filename is None:
        importer = importer if importer else importlib.import_module
        module = importer(cache.modulename)
        filename = module.__file__
        filename.replace(".py", ".ghost_funcs.yml")
        cache.filename = filename

    content = yaml_pretty_dump(cache.model_dump(exclude_defaults=True))
    with open(filename, 'wb') as f:
        f.write(content.encode('utf-8'))


DEFAULT_GHOST_FUNCTION_PROMPT = """
# Instruction

You are a ghost function that produce dynamic python code in the runtime, 
to fulfill a target function or method in the certain python context.

The python context is from module `{target_module}`, code details are below:
```python
{module_code}
```

The target's `__qualname__` is `{target_qualname}`, the definition is:

```python
{target_source}
```

This function `{target_qualname}` is the one you shall implements, but you shall not redefine it.
You need to generate a `__main__(args, kwargs)` function which will be automatic executed 
in the outside system to fulfill the `{target_qualname}`.
The arguments and returns of `__main__` are:
'''
:param args: the arguments list of the target function
:param kwargs: the keyword arguments of the target function
:return: tuple(result: any, ok: bool). result is defined by the target function.
- If ok if False, result shall be None, and means you need to observe the printed std-output for observation.
- If ok is True, means the result is the target function result, task completed.

The args, kwargs and result must be the same types as the target function defined.
'''

0. The code you generated shall start with `<moss>` and end with `</moss>`, the outside system will automatically execute the code between the mark.
1. You should try observation at least once to see the code you generated is correct. That means first time ok shall be False.
2. You shall only raise exceptions that defined in the the doc of the target function, otherwise you shall catch it and make an observation.
3. Once you feel your code is correct, generate a new one without any observation and return ok = True.
4. Cause you are in a runtime system that don't act like in a chat. Generate the code only please.
5. You can always observe the variables by printing them, and return (None, False) after it. You'll see them in next turn.
6. All the code you generated shall be in the `__main__` function, don't execute it your self!
"""


class GhostFuncDriver:

    def __init__(
            self, *,
            container: Container,
            cache: GhostFuncCache,
            target_module: str,
            target_file: str,
            target_source: str,
            target_qualname: str,
            caching: bool = True,
            llm_api: str = "",
            max_turns: int = 10,
    ):
        self._container = container
        self._llm_api = llm_api
        self._target_module = target_module
        self._target_file = target_file
        self._target_qualname = target_qualname
        self._target_source = target_source
        self._caching = caching
        self._cache = cache
        self._max_turns = max_turns

    def execute(self, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        thread = None
        if self._caching:
            thread = self._cache.threads.get(self._target_qualname, None)
        if thread is None:
            thread = self._init_thread()
        return self._run(thread, args, kwargs)

    def _run(self, thread: GoThreadInfo, args: List[Any], kwargs: Dict[str, Any]) -> Any:
        """
        run the ghost func with the origin function's args and kwargs.
        :param thread:
        :param args:
        :param kwargs:
        :return: the result for the origin function
        """
        # get generated code from history, run it.
        pycontext = thread.last_turn().pycontext
        generated = pycontext.execute_code
        if self._caching and generated and pycontext.executed:
            thread, result = self._start_with_generated_code(generated, thread, pycontext, args, kwargs)
        else:
            thread, result = self._think(thread, args, kwargs)
        # save thread at last.
        self._save_thread(thread)
        return result

    def _init_pycontext(self) -> PyContext:
        return PyContext(
            module=None,
        )

    def _init_prompt(self, context_code: str) -> str:
        return DEFAULT_GHOST_FUNCTION_PROMPT.format(
            target_module=self._target_module,
            target_qualname=self._target_qualname,
            module_code=context_code,
            target_source=self._target_source,
        )

    def _init_thread(self) -> GoThreadInfo:
        pycontext = self._init_pycontext()
        moss_runtime = self._moss_runtime(pycontext)
        context_code = moss_runtime.prompter().dump_module_prompt()
        instruction = self._init_prompt(context_code)
        system = Role.SYSTEM.new(content=instruction)
        e = EventTypes.ROTATE.new(task_id="", messages=[system], from_task_id="")
        return GoThreadInfo.new(
            event=e,
            pycontext=pycontext,
        )

    def _moss_runtime(self, pycontext: PyContext) -> MossRuntime:
        compiling_module_name = self._target_module
        target_module = importlib.import_module(self._target_module)
        compiler = self._container.force_fetch(MossCompiler)
        # compile the temp module and replace it values by target module
        runtime = compiler.join_context(pycontext).compile(compiling_module_name)
        # update the compiled temporary module with the target module attributes
        runtime.module().__dict__.update(target_module.__dict__)
        runtime.module().__name__ = target_module.__name__
        # so when temporary module execute any code, it will not contaminate target source.
        return runtime

    def _get_llm_api(self) -> LLMApi:
        llms = self._container.force_fetch(LLMs)
        return llms.get_api(self._llm_api)

    def _start_with_generated_code(
            self,
            generated: str,
            thread: GoThreadInfo,
            pycontext: PyContext,
            args: List[Any],
            kwargs: Dict[str, Any],
    ) -> Tuple[GoThreadInfo, Any]:
        result, ok = self._run_code(generated, thread, pycontext, args, kwargs)
        if ok:
            return thread, result
        return self._think(thread, args, kwargs)

    def _think(self, thread: GoThreadInfo, args: List[Any], kwargs: Dict[str, Any]) -> Tuple[GoThreadInfo, Any]:
        turns = 0
        while True:
            result, ok = self._run_turn(thread, args, kwargs)
            if ok:
                return thread, result
            turns += 1
            if turns > self._max_turns:
                raise RuntimeError(f"Exceed max turns {self._max_turns} turns, still not success")

    def _run_turn(self, thread: GoThreadInfo, args: List[Any], kwargs: Dict[str, Any]) -> Tuple[Any, bool]:
        pycontext = thread.last_turn().pycontext
        chat = thread_to_prompt(thread.id, [], thread)
        llm_api = self._get_llm_api()
        message = llm_api.chat_completion(chat)
        thread.append(message)

        code, ok = self._unwrap_message_code(message)
        if not ok:
            thread.new_turn(
                event=EventTypes.ROTATE.new(
                    task_id="",
                    from_task_id="",
                    messages=[Role.SYSTEM.new(content=code)],
                )
            )
            return None, False
        return self._run_code(code, thread, pycontext, args, kwargs)

    def _run_code(
            self,
            code: str,
            thread: GoThreadInfo,
            pycontext: PyContext,
            args: List[Any],
            kwargs: Dict[str, Any],
    ) -> Tuple[Any, bool]:
        runtime = self._moss_runtime(pycontext)
        pycontext.execute_code = code
        pycontext.executed = True
        executed = None
        try:
            executed = runtime.execute(code=code, target="__main__", kwargs={"args": args, "kwargs": kwargs})
        except Exception as e:
            if not self._ask_confirm_error(thread, e):
                message = Role.SYSTEM.new(content=f"Error occur: {e}")
                thread.new_turn(
                    event=EventTypes.ROTATE.new(task_id="", messages=[message], from_task_id="")
                )
                return None, False
        finally:
            runtime.close()

        result, ok = executed.returns
        if not ok:
            message = Role.SYSTEM.new(content=executed.std_output)
            thread.new_turn(
                event=EventTypes.ROTATE.new(task_id="", messages=[message], from_task_id=""),
            )
            return None, False
        return result, True

    def _ask_confirm_error(self, thread: GoThreadInfo, error: Exception) -> bool:
        chat = thread_to_prompt(thread.id, [], thread)
        chat.added.append(
            Role.SYSTEM.new(
                content=f"Catch Error: {error} \nIf the error is expected, return `ok`, otherwise return `false`"
            )
        )
        llm_api = self._get_llm_api()
        message = llm_api.chat_completion(chat)
        return message.get_content() == "ok"

    @staticmethod
    def _unwrap_message_code(message: Message) -> Tuple[str, bool]:
        content = message.get_content()
        splits = content.split('<moss>', 2)
        if len(splits) < 2:
            return "Error: You shall generated code between <moss> and </moss>", False,
        code = splits[1]
        splits = code.split('</moss>', 2)
        return splits[0], True

    def _save_thread(self, thread: GoThreadInfo) -> None:
        self._cache.threads[self._target_qualname] = thread

    def destroy(self) -> None:
        if hasattr(self, '_cache'):
            del self._cache
        if hasattr(self, '_container'):
            del self._container
