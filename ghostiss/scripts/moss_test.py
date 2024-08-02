from typing import Optional, Type, ClassVar
import sys
import argparse
import os
import yaml
from ghostiss.core.moss.reflect import ClassSign, Interface
from ghostiss.container import Container, Provider, CONTRACT
from ghostiss.core.messages import DefaultTypes
from ghostiss.core.ghosts import Operator, Mindflow
from ghostiss.contracts.storage import Storage, FileStorageProvider
from ghostiss.contracts.configs import ConfigsByStorageProvider
from ghostiss.core.runtime.threads import MsgThread
from ghostiss.core.moss import MOSS, BasicPythonMOSSImpl, BasicModulesProvider
from ghostiss.framework.messengers import TestMessengerProvider
from ghostiss.framework.llms import ConfigBasedLLMsProvider
from ghostiss.framework.moss.runner import MOSSRunnerTestSuite, MOSSRunnerTestResult
from ghostiss.framework.llms.test_case import ChatCompletionTestCase, APIInfo
from ghostiss.helpers import yaml_pretty_dump
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

"""
基于 MOSS Runner 来实现 MOSS 的测试脚本. 
"""

# 输出环节.
console = Console()


class MOSSTestProvider(Provider):
    moss_doc: ClassVar[str] = """
Model-oriented Operating System Simulation (MOSS).
You can use the api that MOSS provided to implement your plan.
"""

    def singleton(self) -> bool:
        return False

    def contract(self) -> Type[CONTRACT]:
        return MOSS

    def factory(self, con: Container) -> Optional[CONTRACT]:
        from ghostiss.core.moss import Importing, Typing
        from abc import ABC, abstractmethod
        import typing
        from pydantic import BaseModel, Field
        from typing import TypedDict
        from ghostiss.core.messages import Message, MessageType, MessageClass
        args = []
        args.extend([
            ClassSign(cls=Message),
            Typing(typing=MessageType, name="MessageType"),
            ClassSign(cls=MessageClass),
        ])
        args.extend(Importing.iterate(values=[ABC, abstractmethod], module='abc'))
        args.extend(Importing.iterate(values=[BaseModel, Field], module='pydantic'))
        args.extend([
            ClassSign(cls=Operator),
            Interface(cls=Mindflow),
        ])
        kwargs = {
            'typing': Importing(value=typing, module='typing'),
            'TypedDict': Importing(value=TypedDict, module='typing'),
        }
        return BasicPythonMOSSImpl(container=con, doc=self.moss_doc).new(
            *args,
            **kwargs,
        )


def _prepare_container() -> Container:
    container = Container()
    # 注册一个假的 messenger.
    container.register(TestMessengerProvider())
    # 注册 moss 相关.
    container.register(BasicModulesProvider())
    container.register(MOSSTestProvider())
    # 注册 llms 配置.
    ghostiss_dir = os.path.abspath(os.path.dirname(__file__) + "/../../demo/ghostiss")
    container.register(FileStorageProvider(ghostiss_dir))
    container.register(ConfigsByStorageProvider("configs"))
    # 准备 llms
    container.register(ConfigBasedLLMsProvider("llms/llms_conf.yaml"))
    return container


def json_format(data: str) -> Markdown:
    return Markdown(f"""
```json
{data}
```
""")


def get_thread(storage: Storage, root_path: str, suite: MOSSRunnerTestSuite) -> MsgThread:
    """
    """
    if not suite.last_round:
        return suite.thread
    last_round = suite.last_round
    current_thread = suite.thread
    last_suite_path = os.path.join(root_path, last_round)
    last_suite = get_suite(storage, last_suite_path)
    history_thread = get_thread(storage, root_path, last_suite)
    history_messages = history_thread.updated().messages + current_thread.messages
    return current_thread.model_copy(update=dict(messages=history_messages))


def get_suite(storage: Storage, suite_file_name: str) -> MOSSRunnerTestSuite:
    content = storage.get(suite_file_name)
    if content is None:
        raise FileNotFoundError(f"file {suite_file_name} not found")

    data = yaml.safe_load(content)
    suite = MOSSRunnerTestSuite(**data)
    return suite


def get_round_filename(origin_file_name: str, r: int) -> str:
    if r == 0:
        return origin_file_name
    file_basename = origin_file_name.rstrip('.yaml')
    return file_basename + "-" + str(r) + ".yaml"


def save_suite(storage: Storage, suite: MOSSRunnerTestSuite, filename: str) -> None:
    data = yaml_pretty_dump(suite.model_dump(exclude_defaults=True))
    storage.put(filename, bytes(data.encode("utf-8")))
    console.print(f"save the suite case {filename}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="run ghostiss runner test cases which located at demo/ghostiss/tests/moss_tests",
    )

    parser.add_argument(
        "--case", "-c",
        help="file name of the case without .yaml suffix",
        type=str,
        default="hello_world"
    )
    parser.add_argument(
        "--llm_test", "-l",
        help="save the chat case to the same file name in the llm test cases",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--save", "-s",
        help="save the test results to the case",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--round", "-r",
        help="round number. if given, will recursively join each 0 ~ current round to a new thread run test, "
             "and save a new round for next run.",
        type=int,
        default=None,
    )
    parser.add_argument(
        "--input", "-i",
        help="input content that replace the current thread inputs",
        type=str,
        default=None,
    )

    container = _prepare_container()
    parsed = parser.parse_args(sys.argv[1:])
    storage = container.force_fetch(Storage)
    root_path = "tests/moss_tests/"
    origin_suite_file_name = os.path.join(root_path, parsed.case + ".yaml")
    suite_file_name = origin_suite_file_name

    if parsed.round:
        suite_file_name = get_round_filename(origin_suite_file_name, parsed.round)
        console.print(f"real loaded file is {suite_file_name}")

    # 获取 suite.
    suite = get_suite(storage, suite_file_name)

    # 递归生成 thread 信息.
    thread = get_thread(storage, root_path, suite)
    if parsed.input:
        input_msg = DefaultTypes.DEFAULT.new_user(content=parsed.input)
        thread.inputs = [input_msg]
        if not suite.thread.inputs:
            suite.thread.inputs = thread.inputs
            save_suite(storage, suite, suite_file_name)
            console.print(f"update the suite inputs to {thread.inputs}")

    if not suite.thread.inputs:
        raise AttributeError(f"thread inputs is empty. You can use --input to add one, or modify test case directly.")

    if parsed.round and suite.round_api and len(suite.llm_apis) > 0:
        suite.llm_apis = [suite.round_api]
        console.print(f"suite.llm_apis replaced to {suite.llm_apis}")

    # 先输出 thread 完整信息
    thread_json = json_format(thread.model_dump_json(indent=2, exclude_defaults=True))
    console.print(Panel(thread_json, title="thread info"))

    # 并发调用 runner.
    results = suite.run_test(container, thread)

    chat_completion_test_case: Optional[ChatCompletionTestCase] = None
    # 输出不同模型生成的 chatinfo.
    for api_name, _result in results.items():
        _thread, _chat, _op = _result
        title = api_name
        # 输出 chat 信息.
        console.print(
            Panel(
                json_format(_chat.model_dump_json(exclude_defaults=True, indent=2)),
                title=f"{title}: chat info"
            ),
        )
        # 用 markdown 输出 chat info.
        lines = []
        for msg in _chat.get_messages():
            content = f"> {msg.role}:\n\n{msg.get_content()}"
            lines.append(content)
        console.print(Panel(
            Markdown("\n\n----\n\n".join(lines)),
            title=f"{title}: chat info in markdown"
        ))

        # 用来丰富 chat completion test.
        if chat_completion_test_case is None:
            chat_completion_test_case = ChatCompletionTestCase(
                chat=_chat,
                apis=[APIInfo(api=api_name)],
            )
        else:
            chat_completion_test_case.apis.append(APIInfo(api=api_name))

    test_result = MOSSRunnerTestResult()
    # 输出 appending 信息.
    for api_name, _result in results.items():
        _thread, _chat, _op = _result
        test_result.results[api_name] = _thread.appending
        title = api_name
        # 输出 appending 的消息.
        appending = _thread.appending
        for msg in appending:
            # 输出 appending 消息体.
            console.print(
                Panel(
                    json_format(msg.model_dump_json(exclude_defaults=True, indent=2)),
                    title=f"{title}: appending message json",
                ),
            )
            content = f"{msg.content} \n\n----\n\n {msg.memory}"
            # 用 markdown 输出消息的 content 和 memory.
            panel = Panel(Markdown(content), title=f" {title}: appending message")
            console.print(panel)
            for caller in msg.callers:
                if caller.name == "moss":
                    console.print(
                        Panel(
                            Markdown("```python\n\n" + caller.arguments + "\n```"),
                            title=f"{title}: generated moss code"
                        )
                    )
        console.print(Panel(str(_op), title=f" {title}: operator output"))

    if parsed.save:
        suite.results.insert(0, test_result)
        save_suite(storage, suite, suite_file_name)
        console.print("save the test results to the case")

    if parsed.round is not None:
        new_round = parsed.round + 1
        new_round_file_name = get_round_filename(origin_suite_file_name, new_round)
        new_suite = suite.model_copy(deep=True)
        new_suite.results = []
        new_suite.last_round = suite_file_name.lstrip(root_path)
        new_round_api = suite.round_api if suite.round_api else suite.llm_apis[0]
        new_suite.round_api = new_round_api
        # 获取新的 message.
        messages = test_result.results[new_round_api]
        new_thread = MsgThread(messages=messages)
        new_suite.thread = new_thread
        new_suite.round_api = new_round_api
        save_suite(storage, new_suite, new_round_file_name)

    if parsed.llm_test:
        llm_test = parsed.case
        llm_test_file_path = os.path.join("tests/llm_tests", llm_test + ".yaml")
        if parsed.round:
            llm_test_file_path = get_round_filename(llm_test_file_path, parsed.round)
        data = yaml_pretty_dump(chat_completion_test_case.model_dump(exclude_defaults=True))
        storage.put(llm_test_file_path, bytes(data.encode("utf-8")))
        console.print(f"save chat test case to {llm_test_file_path}")


if __name__ == "__main__":
    main()
