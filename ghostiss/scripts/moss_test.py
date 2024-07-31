from typing import Optional, Type, ClassVar
import sys
import argparse
import os
import yaml
from ghostiss.reflect import Interface, Library
from ghostiss.container import Container, Provider, CONTRACT
from ghostiss.core.ghosts import Operator, Mindflow
from ghostiss.contracts.storage import Storage, FileStorageProvider
from ghostiss.contracts.configs import ConfigsByStorageProvider
from ghostiss.core.moss import MOSS, BasicMOSSImpl, BasicModulesProvider
from ghostiss.core.ghosts.messenger import TestMessengerProvider
from ghostiss.framework.llms import ConfigBasedLLMsProvider
from ghostiss.framework.runners.mossrunner import MOSSRunnerTestSuite, MOSSRunnerTestResult
from ghostiss.framework.llms.test_case import ChatCompletionTestCase, APIInfo
from ghostiss.helpers import yaml_pretty_dump
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

"""
基于 MOSS Runner 来实现 MOSS 的测试脚本. 
"""


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
        return BasicMOSSImpl(container=con, doc=self.moss_doc).with_vars(
            Interface(cls=Operator),
            Library(cls=Mindflow),
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

    container = _prepare_container()
    parsed = parser.parse_args(sys.argv[1:])
    storage = container.force_fetch(Storage)
    prefix = "tests/moss_tests/"
    suite_file_name = os.path.join(prefix, parsed.case + ".yaml")
    content = storage.get(suite_file_name)
    if content is None:
        raise FileNotFoundError(f"file {suite_file_name} not found")

    data = yaml.safe_load(content)
    suite = MOSSRunnerTestSuite(**data)
    # 输出环节.
    console = Console()

    thread = suite.thread
    # 先输出 thread 完整信息
    thread_json = json_format(thread.model_dump_json(indent=2, exclude_defaults=True))
    console.print(Panel(thread_json, title="thread info"))

    results = suite.run_test(container)

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
        data = yaml_pretty_dump(suite.model_dump(exclude_defaults=True))
        storage.put(suite_file_name, bytes(data.encode("utf-8")))

    if parsed.llm_test:
        llm_test = parsed.case
        llm_test_file_path = os.path.join("tests/llm_tests", llm_test + ".yaml")
        data = yaml_pretty_dump(chat_completion_test_case.model_dump(exclude_defaults=True))
        storage.put(llm_test_file_path, bytes(data.encode("utf-8")))
        console.print(f"save chat test case to {llm_test_file_path}")


if __name__ == "__main__":
    main()
