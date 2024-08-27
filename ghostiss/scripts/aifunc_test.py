import argparse
import sys
import os
from typing import List

from ghostiss.core.session import MsgThread
from ghostiss.scripts.logconf import prepare_logger
from ghostiss.core.llms import Chat
from ghostiss.core.messages import Message
from ghostiss.core.moss import test_container
from ghostiss.core.moss.aifunc import DefaultAIFuncManagerImpl, AIFunc, DefaultAIFuncDriverImpl, AIFuncManager
from ghostiss.framework.logger import FileLoggerProvider
from ghostiss.framework.storage import FileStorageProvider
from ghostiss.framework.llms import ConfigBasedLLMsProvider
from ghostiss.framework.threads import StorageThreadsProvider
from ghostiss.container import Container
from ghostiss.contracts.modules import Modules
from ghostiss.contracts.configs import ConfigsByStorageProvider
from ghostiss.helpers import import_from_path, yaml_pretty_dump
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

console = Console()

prepare_logger()


def prepare_container(root_dir: str) -> Container:
    container = test_container()
    container.register(FileStorageProvider(root_dir))
    container.register(FileLoggerProvider(logger_name="debug"))
    container.register(StorageThreadsProvider(thread_dir='runtime/threads'))
    container.register(ConfigsByStorageProvider("ghostiss/configs"))
    container.register(ConfigBasedLLMsProvider("llms/llms_conf.yaml"))
    return container


def main() -> None:
    parser = argparse.ArgumentParser(
        description="run ghostiss aifunc test cases, show results",
    )
    parser.add_argument(
        "--import_path", '-i',
        help="the import path of the AIFunc instance, such as foo.bar:baz",
        type=str,
        # 默认使用专门测试 MossTestSuite 的文件.
        default="ghostiss.core.moss.aifunc.examples.agentic:example",
    )
    parser.add_argument(
        "--llm_api", '-l',
        help="the llm api name",
        type=str,
        # 默认使用专门测试 MossTestSuite 的文件.
        default="",
    )
    parser.add_argument(
        "--auto", '-a',
        help="auto run the test or stop at each generations",
        action="store_true",
        # 默认使用专门测试 MossTestSuite 的文件.
        default=False,
    )

    parsed = parser.parse_args(sys.argv[1:])
    llm_api = parsed.llm_api
    demo_dir = os.path.abspath(os.path.dirname(__file__) + "/../../demo")
    container = prepare_container(demo_dir)

    class TestDriverImpl(DefaultAIFuncDriverImpl):
        console = console

        def on_message(self, message: Message) -> None:
            self.console.print(
                Panel(
                    Markdown(message.get_content()),
                    title=f"generated message ({self.name()})",
                )
            )
            if not parsed.auto:
                value = Prompt.ask("Continue?", choices=["y", "n"], default="y")
                if value != "y":
                    exit(0)

        def on_chat(self, chat: Chat) -> None:
            for message in chat.get_messages():
                self.console.print(Panel(
                    Markdown(message.get_content()),
                    title=f"chat_info ({self.name()})",
                ))
            if not parsed.auto:
                value = Prompt.ask("Continue?", choices=["y", "n"], default="y")
                if value != "y":
                    exit(0)

        def on_system_messages(self, messages: List[Message]) -> None:
            pass

        def on_save(self, manager: AIFuncManager, thread: MsgThread) -> None:
            current = thread.current
            if current:
                for message in current.messages():
                    self.console.print(
                        Panel(
                            Markdown(message.get_content()),
                            title="thread new round message",
                        )
                    )
            super().on_save(manager, thread)

    manager_ = DefaultAIFuncManagerImpl(
        container=container,
        llm_api_name=llm_api,
        default_driver=TestDriverImpl,
    )
    modules = container.force_fetch(Modules)
    aifunc = import_from_path(parsed.import_path, modules.import_module)
    if not isinstance(aifunc, AIFunc):
        raise AttributeError(f'aifunc must be an instance of {AIFunc}, {aifunc} given')

    driver = manager_.get_driver(aifunc)
    # print initialized thread.
    thread_ = driver.initialize()
    thread_content = yaml_pretty_dump(thread_.model_dump(exclude_defaults=True))
    console.print(Panel(
        Markdown(f"```markdown\n{thread_content}\n```"),
        title="initialized thread",
    ))

    result = manager_.execute(aifunc)
    console.print(result)
    manager_.destroy()


if __name__ == "__main__":
    main()
