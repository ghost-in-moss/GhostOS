import traceback
from typing import Tuple, List, Optional, Any

from ghostos.core.aifunc.interfaces import (
    AIFuncDriver, AIFuncExecutor, ExecStep, ExecFrame, AIFuncRepository,
    TooManyFailureError,
)
from ghostos.core.aifunc.func import (
    AIFunc,
    get_aifunc_instruction, get_aifunc_result_type, get_aifunc_pycontext, get_aifunc_llmapi,
)
from ghostos.core.llms import LLMs, Prompt
from ghostos_moss.abcd import MossRuntime
from ghostos.core.runtime import GoThreadInfo, EventTypes, GoThreads, thread_to_prompt
from ghostos.core.messages import Role, Message, Stream
from ghostos_container import Container

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

    def initialize(self, container: Container, frame: ExecFrame) -> GoThreadInfo:
        pycontext = get_aifunc_pycontext(self.aifunc)
        messages = []
        threads = container.get(GoThreads)
        if threads:
            thread = threads.get_thread(frame.frame_id, create=False)
            if thread:
                return thread
        # create one for frame
        instruction = get_aifunc_instruction(self.aifunc)
        if instruction:
            system_message = Role.SYSTEM.new(
                content=instruction,
            )
            messages.append(system_message)

        event = EventTypes.ROTATE.new(
            task_id="",
            from_task_id="",
            messages=messages,
        )
        thread = GoThreadInfo.new(
            thread_id=frame.frame_id,
            event=event,
            pycontext=pycontext,
        )
        return thread

    def generate_system_messages(self, runtime: MossRuntime) -> List[Message]:
        aifunc_cls = self.aifunc.__class__
        aifunc_class = aifunc_cls.__name__
        aifunc_result_type = get_aifunc_result_type(aifunc_cls)
        aifunc_result_class = aifunc_result_type.__name__
        moss_code = runtime.prompter().dump_module_prompt()
        prompt = default_aifunc_prompt(
            aifunc_class=aifunc_class,
            aifunc_result_class=aifunc_result_class,
            moss_code=moss_code,
        )
        message = Role.SYSTEM.new(content=prompt)
        return [message]

    def on_chat(self, chat: Prompt) -> None:
        pass

    def on_message(self, message: Message, step: ExecStep, upstream: Optional[Stream]) -> None:
        if upstream:
            message = message.model_copy(deep=True)
            message.name = self.aifunc.func_name()
            payload = step.as_payload()
            payload.set_payload(message)
            upstream.deliver(message)

    def on_system_messages(self, messages: List[Message]) -> None:
        pass

    def think(
            self,
            manager: AIFuncExecutor,
            thread: GoThreadInfo,
            step: ExecStep,
            upstream: Optional[Stream]
    ) -> Tuple[GoThreadInfo, Optional[Any], bool]:
        # get compiler by current exec step
        # the MossCompiler.container().get(AIFuncCtx) will bind this step.
        compiler = manager.compiler(step, upstream)
        compiler.join_context(thread.get_pycontext())
        compiler.bind(self.aifunc.__class__, self.aifunc)
        runtime = compiler.compile(None)
        # 使用默认的方法, 将 thread 转成 chat.
        systems = self.generate_system_messages(runtime)
        systems.append(Role.SYSTEM.new(
            content=DEFAULT_NOTICES,
        ))

        # build chat
        self.on_system_messages(systems)
        chat = thread_to_prompt(thread.id, systems, thread)
        step.chat = chat.model_copy(deep=True)
        # on_chat hook
        self.on_chat(chat)

        # instance the llms
        llms = manager.container().force_fetch(LLMs)
        llm_api = get_aifunc_llmapi(self.aifunc, llms)
        if llm_api is None:
            llm_api = manager.default_llm_api()

        # call llm api
        ai_generation = llm_api.chat_completion(chat)

        # append ai_generation
        thread.append(ai_generation)
        step.generate = ai_generation
        # on_message hook
        self.on_message(ai_generation, step, upstream)

        # parse the ai_generation.
        code = self.parse_moss_code_in_message(ai_generation)

        error = None
        # handle code:
        if not code:
            error = Role.new_system(
                content="Error! You shall only write python code! DO NOT ACT LIKE IN A CHAT. "
                        "Generate code in `<code></code>`."
            )

        elif "main(" not in code:
            error = Role.new_system(
                content="Error! No main function found in your generation! use `<code></code>` to wrap your code."
            )

        if error is not None:
            thread.new_turn(
                event=EventTypes.ROTATE.new(
                    messages=[error],
                    task_id=thread.id,
                    from_task_id=thread.id,
                ),
            )
            step.error = error
            self.on_message(error, step, upstream)
            return thread, None, False

        result = None
        # 运行 moss.
        try:
            executed = runtime.execute(
                code=code,
                target='main',
                local_args=['moss'],
                kwargs={"fn": self.aifunc},
            )

            result, finish = executed.returns
            if not isinstance(finish, bool):
                raise RuntimeError(f"Result from main function {finish} is not boolean")

            output = executed.std_output
            step.std_output = output
            if output:
                output_message = Role.new_system(
                    content=f"Observation:\n\nmoss executed main, std output is: \n{output}"
                )
                messages = [output_message]
                self.on_message(output_message, step, upstream)
            else:
                output_message = Role.new_system(
                    content=f"Observation:\n\nhave not printed anything"
                )
                messages = [output_message]
            pycontext = executed.pycontext

            # append the messages.
            thread.new_turn(
                event=EventTypes.ROTATE.new(
                    messages=messages,
                    task_id=thread.id,
                    from_task_id=thread.id,
                ),
                pycontext=pycontext,
            )
            step.pycontext = pycontext
            # I think this method is thread-safe
            step.messages.extend(messages)
            self.error_times = 0
        except TooManyFailureError:
            raise
        except Exception as e:
            exe_info = "\n".join(traceback.format_exception(e)[-5:])
            output_message = Role.new_system(
                content=f"moss executed main, exception occurs: \n{exe_info}"
            )
            thread.new_turn(
                event=EventTypes.ROTATE.new(
                    messages=[output_message],
                    task_id=thread.id,
                    from_task_id=thread.id,
                ),
            )
            step.error = output_message
            self.on_message(output_message, step, upstream)
            self.error_times += 1
            if self.error_times >= 3:
                raise TooManyFailureError(f"AIFunc `{self.name()}` failed {self.error_times} times, can not fix itself: \n{e}")
            else:
                finish = False
        finally:
            runtime.close()
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

    def on_save(self, container: Container, frame: ExecFrame, step: ExecStep, thread: GoThreadInfo) -> None:
        # 如果 threads 抽象存在, 就保存一下. 还应该做一些日志的工作.
        threads = container.get(GoThreads)
        if threads is not None:
            threads.save_thread(thread)
        repo = container.get(AIFuncRepository)
        if repo is not None:
            repo.save_exec_frame(frame)
