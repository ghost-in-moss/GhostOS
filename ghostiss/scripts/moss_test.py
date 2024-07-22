import sys
import argparse
import os
import json
from typing import Optional, Type, ClassVar

import yaml
from ghostiss.container import Container, Provider, CONTRACT
from ghostiss.core.ghosts import Operator
from ghostiss.contracts.storage import Storage, FileStorageProvider
from ghostiss.contracts.configs import ConfigsByStorageProvider
from ghostiss.core.moss import MOSS, BasicMOSSImpl, Interface, BasicModulesProvider
from ghostiss.framework.llms import ConfigBasedLLMsProvider
from ghostiss.framework.runners.mossrunner import MOSSRunnerTestSuite
from ghostiss.core.messages.messenger import TestMessengerProvider
from rich.console import Console
from rich.panel import Panel
from rich.json import JSON

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
        "--chat", "-a",
        default=False,
        action="store_true",
        help="show chat messages only",
    )
    container = _prepare_container()
    parsed = parser.parse_args(sys.argv[1:])
    storage = container.force_fetch(Storage)
    prefix = "tests/moss_tests/"
    file_name = os.path.join(prefix, parsed.case + ".yaml")
    content = storage.get(file_name)
    if content is None:
        raise FileNotFoundError(f"file {file_name} not found")

    data = yaml.safe_load(content)
    suite = MOSSRunnerTestSuite(**data)
    # 输出环节.
    console = Console()
    # 只输出 chat.
    if parsed.chat:
        thread = suite.thread
        _, chat = suite.get_runner().prepare(container, thread)
        messages = chat.get_messages()
        dump = []
        for message in messages:
            dump.append(message.model_dump(exclude_defaults=True))
        thread_json = JSON(json.dumps(dump), indent=2)
        console.print(thread_json)
        return

    # 执行 test.
    thread, op = suite.run_test(container)
    thread_json = JSON(thread.model_dump_json(indent=2, exclude_defaults=True))
    console.print(Panel(thread_json, title="thread output"))
    console.print(Panel(str(op), title="operator output"))


if __name__ == "__main__":
    main()
