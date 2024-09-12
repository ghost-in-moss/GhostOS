import traceback
from typing import Tuple, List, Optional, Any

from ghostos.core.moss.aifunc.interfaces import AIFuncDriver, AIFuncManager
from ghostos.core.moss.aifunc.func import (
    AIFunc,
    get_aifunc_instruction, get_aifunc_result_type, get_aifunc_pycontext, get_aifunc_llmapi,
)
from ghostos.core.llms import LLMs, Chat
from ghostos.core.moss.abc import MossRuntime
from ghostos.core.session import MsgThread, DefaultEventType, Threads, thread_to_chat
from ghostos.core.messages import Role, Message
from ghostos.contracts.logger import LoggerItf

__all__ = [
    'DefaultAIFuncDriverImpl',
]

DEFAULT_AI_FUNC_PROMPT = """
# Who Are You 

You are an AIFunc named `{aifunc_class}`.
AIFunc is a LLM-driven function that could complete request by multi-turns thinking,
And your purpose is to generate AIFuncResult `{aifunc_result_class}` as final result.

## MOSS

You are equipped with a MOSS (model-oriented operating system simulation) in which you can generate Python code and 
python libraries to reach your goal.

The `PYTHON CONTEXT` that MOSS already provide to you are below: 

```python
{moss_code}
```

You shall generate a single block of Python code, 
and in the code you shall defines a main function like: 
`def main(moss: Moss, fn: {aifunc_class}):`

about the params and returns:
:param moss: A Moss instance
:param fn: An instance of {aifunc_class}
:return: tuple[result:{aifunc_result_class} | None , ok: bool]
If ok is False, means you need to observe the output that you print in the function, and think another round.
If ok is True, means you finish the request and return a final result.

The MOSS will automatically execute the main function you generated with the instance of class Moss, 
take next step based on the returns. 

So you shall not repeat the exists code that already provide in the `PYTHON CONTEXT`.
"""

CODE_MARK_LEFT = "<code>"
CODE_MARK_RIGHT = "</code>"

DEFAULT_NOTICES = f"""
## Notices
- The code you generated shall start with {CODE_MARK_LEFT} and end with {CODE_MARK_RIGHT}, the outside system will automatically execute the code between the mark.
- You can import basic python module if you needed. 
- The variables defined in the main function will not keep in memory during multi-turns thinking. Unless some lib (AIFuncCtx) provide the ability.
- MOSS will automatic execute the main function so YOU SHOULD NEVER EXECUTE IT YOURSELF.
- If you are not equipped enough to resolve your quest, you shall admit the it in the result or raise an exception.
- **You are not Agent, DO NOT TALK ABOUT YOUR THOUGHT, JUST WRITE THE CODES ONLY**
"""


def default_aifunc_prompt(
        *,
        aifunc_class: str,
        aifunc_result_class: str,
        moss_code: str,
) -> str:
    return DEFAULT_AI_FUNC_PROMPT.format(
        aifunc_class=aifunc_class,
        aifunc_result_class=aifunc_result_class,
        moss_code=moss_code,
    )


class DefaultAIFuncDriverImpl(AIFuncDriver):

    def __init__(self, fn: AIFunc):
        self.error_times = 0
        self.max_error_times = 3
        super().__init__(fn)

    def name(self) -> str:
        return self.aifunc.__class__.__name__

    def initialize(self) -> MsgThread:
        pycontext = get_aifunc_pycontext(self.aifunc)
        messages = []
        instruction = get_aifunc_instruction(self.aifunc)
        if instruction:
            system_message = Role.SYSTEM.new(
                content=instruction,
            )
            messages.append(system_message)

        event = DefaultEventType.INPUT.new(
            task_id="",
            from_task_id="",
            messages=messages,
        )
        thread = MsgThread.new(
            event=event,
            pycontext=pycontext,
        )
        return thread

    def generate_system_messages(self, runtime: MossRuntime) -> List[Message]:
        aifunc_cls = self.aifunc.__class__
        aifunc_class = aifunc_cls.__name__
        aifunc_result_type = get_aifunc_result_type(aifunc_cls)
        aifunc_result_class = aifunc_result_type.__name__
        moss_code = runtime.prompter().dump_context_prompt()
        prompt = default_aifunc_prompt(
            aifunc_class=aifunc_class,
            aifunc_result_class=aifunc_result_class,
            moss_code=moss_code,
        )
        message = Role.SYSTEM.new(content=prompt)
        return [message]

    def on_chat(self, chat: Chat) -> None:
        pass

    def on_message(self, message: Message) -> None:
        pass

    def on_system_messages(self, messages: List[Message]) -> None:
        pass

    def think(self, manager: AIFuncManager, thread: MsgThread) -> Tuple[MsgThread, Optional[Any], bool]:
        logger = manager.container().get(LoggerItf)
        compiler = manager.compiler()
        compiler.join_context(thread.get_pycontext())
        compiler.bind(self.aifunc.__class__, self.aifunc)
        runtime = compiler.compile(None)
        # 使用默认的方法, 将 thread 转成 chat.
        systems = self.generate_system_messages(runtime)
        systems.append(Role.SYSTEM.new(
            content=DEFAULT_NOTICES,
        ))
        self.on_system_messages(systems)
        chat = thread_to_chat(thread.id, systems, thread)
        self.on_chat(chat)  # Whether you want to send chat to llm, let it generate code for you or not
        # todo: log
        # 实例化 llm api
        llms = manager.container().force_fetch(LLMs)
        llm_api = get_aifunc_llmapi(self.aifunc, llms)
        if llm_api is None:
            llm_api = manager.default_llm_api()
        # 调用 llm api
        # logger and logger.info(f"run aifunc with chat :{chat}")
        ai_generation = llm_api.chat_completion(chat)
        # 插入 ai 生成的消息.
        thread.append(ai_generation)
        self.on_message(ai_generation)  # Whether you want to execute the ai-generated code or not
        code = self.parse_moss_code_in_message(ai_generation)

        # code 相关校验:
        if not code:
            thread.append(Role.SYSTEM.new(content="Error! You shall only write python code! DO NOT ACT LIKE IN A CHAT"))
            logger.error(f"ai_generation: {repr(ai_generation)}")
            return thread, None, False
        if "main(" not in code:
            thread.append(Role.SYSTEM.new(content="Error! No main function found in your generation!"))
            return thread, None, False

        result = None
        # 运行 moss.
        try:
            executed = runtime.execute(code=code, target='main', local_args=['moss'], kwargs={"fn": self.aifunc})
            result, finish = executed.returns
            if not isinstance(finish, bool):
                raise RuntimeError(f"Result from main function {finish} is not boolean")

            outputs = executed.std_output
            if outputs:
                output_message = Role.SYSTEM.new(
                    content=f"moss executed main, std output is: \n{outputs}"
                )
                messages = [output_message]
            else:
                messages = []
            pycontext = executed.pycontext
            thread.new_turn(
                event=DefaultEventType.OBSERVE.new(
                    messages=messages,
                    task_id=thread.id,
                    from_task_id=thread.id,
                ),
                pycontext=pycontext,
            )
            self.error_times = 0
        except Exception as e:
            exe_info = "\n".join(traceback.format_exception(e)[-5:])
            output_message = Role.SYSTEM.new(
                content=f"moss executed main, exception occurs: \n{exe_info}"
            )
            thread.new_turn(
                event=DefaultEventType.OBSERVE.new(
                    messages=[output_message],
                    task_id=thread.id,
                    from_task_id=thread.id,
                ),
            )
            self.error_times += 1
            if self.error_times >= 3:
                raise RuntimeError(f"AIFunc `{self.name()}` failed {self.error_times} times, can not fix itself: \n{e}")
            else:
                finish = False
        finally:
            runtime.destroy()
        return thread, result, finish

    def parse_moss_code_in_message(self, message: Message) -> str:
        content = message.content

        code_start_index = content.find(CODE_MARK_LEFT)
        if code_start_index == -1:
            return ""
        code_end_index = content.rfind(CODE_MARK_RIGHT)
        if code_end_index == -1:
            return ""

        return content[code_start_index + len(CODE_MARK_LEFT): code_end_index].strip()

    def on_save(self, manager: AIFuncManager, thread: MsgThread) -> None:
        # 如果 threads 抽象存在, 就保存一下. 还应该做一些日志的工作.
        container = manager.container()
        threads = container.get(Threads)
        if threads is not None:
            threads.save_thread(thread)
