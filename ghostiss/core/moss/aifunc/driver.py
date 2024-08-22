from typing import Tuple, List, Optional, Any

from ghostiss.core.moss.aifunc.interfaces import AIFuncDriver, AIFuncManager
from ghostiss.core.moss.aifunc.func import (
    get_aifunc_instruction, get_aifunc_result_type, get_aifunc_pycontext, get_aifunc_llmapi,
)
from ghostiss.core.llms import LLMs
from ghostiss.core.moss.abc import MossRuntime
from ghostiss.core.session import MsgThread, DefaultEventType, Threads, thread_to_chat
from ghostiss.core.messages import Role, Message

__all__ = [
    'DefaultAIFuncDriverImpl',
]

DEFAULT_AI_FUNC_PROMPT = """
# Who Are You 

You are an AIFunc named `{aifunc_name}`.
AIFunc is a LLM-driven function that could complete request by multi-turns thinking,
and your purpose is to generate AIFuncResult `{aifunc_result_type_name}`.

## MOSS

You are equipped with a MOSS (model-oriented operating system simulation) in which you can use Python code and 
python libraries to reach your goal.

The Python context that moss provide to you are below: 

```python
{moss_code}
```

With MOSS you shall generate a single block of Python code, 
and in the code you shall defines a function `def main(os: MOSS) -> bool:`.
The MOSS will compile your code to the context, 
then automatically execute the main function with IoC injection for class Moss, 
and take next step based on the returns from the main function:  

- if the main function returns `False`, means you need another round of thinking, to observe the outputs you printed.
- if returns `True`, means you have set the `__result__` variable as the final result of the request.

## Notices

* Your final mission is to generate a value in type `{aifunc_result_type_name}` to the `__result__` variable.
* The variables defined in the main function will not keep in memory during multi-turns thinking. Unless some lib provide the ability.
* cause you are in the multi-turns thinking mode, you shall not act like in a chat, do not say anything but coding.
* so just generate the code for the MOSS, put your thought as comment in it. 
* MOSS will automatic execute the main function so YOU SHOULD NEVER EXECUTE IT YOURSELF.
* If you are not equipped enough to resolve your quest, you shall admit the it to __result__ or raise an exception.
"""


def default_aifunc_prompt(
        *,
        aifunc_name: str,
        aifunc_result_type_name: str,
        moss_code: str,
) -> str:
    return DEFAULT_AI_FUNC_PROMPT.format(
        aifunc_name=aifunc_name,
        aifunc_result_type_name=aifunc_result_type_name,
        moss_code=moss_code,
    )


class DefaultAIFuncDriverImpl(AIFuncDriver):

    def initialize(self) -> MsgThread:
        instruction = get_aifunc_instruction(self.aifunc)
        pycontext = get_aifunc_pycontext(self.aifunc)
        system_message = Role.SYSTEM.new(
            content=instruction,
        )
        event = DefaultEventType.THINK.new(
            task_id="",
            from_task_id="",
            messages=[system_message],
        )
        thread = MsgThread.new(
            event=event,
            pycontext=pycontext,
        )
        return thread

    def generate_system_messages(self, runtime: MossRuntime) -> List[Message]:
        aifunc_cls = self.aifunc.__class__
        aifunc_name = aifunc_cls.__name__
        aifunc_result_type = get_aifunc_result_type(aifunc_cls)
        aifunc_result_type_name = aifunc_result_type.__name__
        moss_code = runtime.prompter().dump_context_prompt()
        prompt = default_aifunc_prompt(
            aifunc_name=aifunc_name,
            aifunc_result_type_name=aifunc_result_type_name,
            moss_code=moss_code,
        )
        message = Role.SYSTEM.new(content=prompt)
        return [message]

    def think(self, manager: AIFuncManager, thread: MsgThread) -> Tuple[MsgThread, Optional[Any], bool]:
        compiler = manager.compiler()
        runtime = compiler.join_context(thread.get_pycontext()).compile("__aifunc__")
        # 使用默认的方法, 将 thread 转成 chat.
        systems = self.generate_system_messages(runtime)
        chat = thread_to_chat(thread.id, systems, thread)
        # todo: log
        # 实例化 llm api
        llms = manager.container().force_fetch(LLMs)
        llm_api = get_aifunc_llmapi(self.aifunc, llms)
        if llm_api is None:
            llm_api = manager.default_llm_api()
        # 调用 llm api
        message = llm_api.chat_completion(chat)
        code = self.parse_moss_code_in_message(message)

        result = None
        # 运行 moss.
        try:
            finish = runtime.execute(code=code, target='main', args=['moss'])
            if not isinstance(finish, bool):
                raise RuntimeError(f"Result from main function {finish} is not boolean")
            if finish:
                result = runtime.locals().get("__result__", None)

            outputs = runtime.dump_std_output()
            output_message = Role.SYSTEM.new(
                content=f"moss executed main, std output is: \n{outputs}"
            )
            pycontext = runtime.dump_pycontext()
            thread.new_turn(
                event=DefaultEventType.THINK.new(
                    messages=[output_message],
                    task_id=thread.id,
                    from_task_id=thread.id,
                ),
                pycontext=pycontext,
            )
        except Exception as e:
            output_message = Role.SYSTEM.new(
                content=f"moss executed main, exception occurs: \n{e}"
            )
            thread.new_turn(
                event=DefaultEventType.THINK.new(
                    messages=[output_message],
                    task_id=thread.id,
                    from_task_id=thread.id,
                ),
            )
            finish = True
        finally:
            runtime.destroy()
        return thread, result, finish

    def parse_moss_code_in_message(self, message: Message) -> str:
        content = message.content
        splits = content.split('```python\n')
        if len(splits) > 1:
            content = splits[1]
            splits = content.split('```')
            content = splits[0]
        return content.strip()

    def on_save(self, manager: AIFuncManager, thread: MsgThread) -> None:
        # 如果 threads 抽象存在, 就保存一下. 还应该做一些日志的工作.
        container = manager.container()
        threads = container.get(Threads)
        if threads is not None:
            threads.save_thread(thread)
