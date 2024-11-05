import argparse
import sys
import os
import yaml
from typing import List, Dict

from ghostos.core.session import GoThreadInfo
from logging.config import dictConfig
from ghostos.core.llms import Prompt
from ghostos.core.messages import Message
from ghostos.core.moss import test_container
from ghostos.core.aifunc import (
    DefaultAIFuncExecutorImpl, AIFunc, DefaultAIFuncDriverImpl, AIFuncExecutor,
    AIFuncResult,
)
from ghostos.framework.logger import NamedLoggerProvider
from ghostos.framework.storage import FileStorageProvider
from ghostos.framework.llms import ConfigBasedLLMsProvider
from ghostos.framework.threads import MsgThreadRepoByStorageProvider
from ghostos.framework.configs import ConfigsByStorageProvider
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

__all__ = ['run_aifunc']

console = Console()


def init_logger(conf_path: str):
    with open(conf_path) as f:
        content = f.read()
    data = yaml.safe_load(content)
    dictConfig(data)


def run_aifunc(
        root_dir: str,
        aifunc: AIFunc,
        logger_conf_path: str = "configs/logging.yml",
        logger_name: str = "debug",
        threads_path: str = "runtime/threads",
        configs_path: str = "configs",
        llm_conf_path: str = "llms_conf.yml",
        llm_api_name: str = "",
        debug: bool = True,
) -> AIFuncResult:
    # prepare logger
    absolute_logger_conf = os.path.join(root_dir, logger_conf_path)
    init_logger(absolute_logger_conf)

    # prepare container
    container = test_container()
    container.register(FileStorageProvider(root_dir))
    container.register(NamedLoggerProvider(logger_name=logger_name))
    container.register(MsgThreadRepoByStorageProvider(threads_dir=threads_path))
    container.register(ConfigsByStorageProvider(configs_path))
    container.register(ConfigBasedLLMsProvider(llm_conf_path))

    class TestDriverImpl(DefaultAIFuncDriverImpl):
        console = console

        def on_message(self, message: Message) -> None:
            self.console.print(
                Panel(
                    Markdown(message.get_content()),
                    title=f"generated message ({self.name()})",
                )
            )
            if debug:
                value = Prompt.ask("Continue?", choices=["y", "n"], default="y")
                if value != "y":
                    exit(0)

        def on_chat(self, chat: Prompt) -> None:
            for message in chat.get_messages():
                self.console.print(Panel(
                    Markdown(message.get_content()),
                    title=f"chat_info ({self.name()})",
                ))
            if debug:
                value = Prompt.ask("Continue?", choices=["y", "n"], default="y")
                if value != "y":
                    exit(0)

        def on_system_messages(self, messages: List[Message]) -> None:
            pass

        def on_save(self, manager: AIFuncExecutor, thread: GoThreadInfo) -> None:
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

    manager = DefaultAIFuncExecutorImpl(
        container=container,
        llm_api_name=llm_api_name,
        default_driver=TestDriverImpl,
    )
    try:
        return manager.execute(aifunc)
    finally:
        manager.destroy()
