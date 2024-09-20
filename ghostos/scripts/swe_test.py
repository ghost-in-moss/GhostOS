import argparse
import sys
import os
import yaml
from typing import List, Dict

from ghostos.core.session import MsgThread
from ghostos.scripts.logconf import prepare_logger
from ghostos.core.llms import Chat
from ghostos.core.messages import Message
from ghostos.core.moss import test_container
from ghostos.core.aifunc import DefaultAIFuncManagerImpl, AIFunc, DefaultAIFuncDriverImpl, AIFuncManager
from ghostos.framework.logger import NamedLoggerProvider
from ghostos.framework.storage import FileStorageProvider
from ghostos.framework.llms import ConfigBasedLLMsProvider
from ghostos.framework.threads import StorageThreadsProvider
from ghostos.container import Container
from ghostos.contracts.modules import Modules
from ghostos.framework.configs import ConfigsByStorageProvider
from ghostos.helpers import import_from_path, yaml_pretty_dump
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt


console = Console()

prepare_logger()


def prepare_container(root_dir: str) -> Container:
    container = test_container()
    container.register(FileStorageProvider(root_dir))
    container.register(NamedLoggerProvider(logger_name="debug"))
    container.register(StorageThreadsProvider(threads_dir='runtime/threads'))
    container.register(ConfigsByStorageProvider("ghostos/configs"))
    container.register(ConfigBasedLLMsProvider("llms/llms_conf.yaml"))
    return container


def main() -> None:
    parser = argparse.ArgumentParser(
        description="run swe-evaluation aifunc test cases, show results",
    )
    parser.add_argument(
        "--case", '-c',
        help="ghostos aifunc test case name in demo/ghostos/tests/aifunc_tests.yml",
        type=str,
        default="",
    )
    parser.add_argument(
        "--import_path", '-i',
        help="the import path of the AIFunc instance, such as foo.bar:baz",
        type=str,
        default="evaluation.swe_bench_lite.debug_localization:example",
    )
    parser.add_argument(
        "--llm_api", '-l',
        help="the llm api name",
        type=str,
        default="",
    )
    parser.add_argument(
        "--auto", '-a',
        help="auto run the test or stop at each generations",
        action="store_true",
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
