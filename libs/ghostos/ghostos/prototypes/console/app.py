from __future__ import annotations
import asyncio
from typing import Optional, List

from ghostos.abcd import GhostOS, Ghost, Background
from ghostos_container import Provider
from ghostos.contracts.logger import get_console_logger
from ghostos.core.messages import Message, Role, MessageType, Receiver
from ghostos.framework.messages import TaskPayload
from ghostos.core.runtime import Event
from queue import Queue, Empty
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.patch_stdout import patch_stdout
from prompt_toolkit.shortcuts import PromptSession
from threading import Lock
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.status import Status

__all__ = ['ConsoleApp']


class ConsoleApp(Background):

    def __init__(
            self, *,
            ghostos: GhostOS,
            ghost: Ghost,
            username: str,
            debug: bool = False,
            shell_name: str = "console",
            shell_id: Optional[str] = None,
            process_id: Optional[str] = None,
            worker_num: int = 4,
            welcome_user_message: Optional[str] = None,
            on_create_message: Optional[str] = None,
            providers: Optional[List[Provider]] = None,
    ):
        self._os = ghostos
        self._ghost = ghost
        self._username = username
        self._shell_name = shell_name
        self._shell_id = shell_id if shell_id else shell_name
        self._process_id = process_id
        self._console = Console()
        self._logger = get_console_logger()
        self._closed = False
        self._stopped = False
        self._main_queue = Queue()
        self._thread_locker = Lock()
        self._debug = debug
        self._worker_num = worker_num
        if not welcome_user_message:
            welcome_user_message = "the conversation is going to begin, please welcome user"
        self._welcome_user_message = welcome_user_message
        self._on_create_message = on_create_message
        self._main_task_id = ""
        session = PromptSession("\n\n<<< ", )
        self._prompt_session = session
        self._shell = self._os.create_matrix(
            self._shell_name,
            process_id=self._process_id,
            providers=providers,
        )
        self._conversation = self._shell.sync(self._ghost)

    def __del__(self):
        self.close()
        self._conversation.close()
        self._shell.close()

    def run(self):
        # self._shell.background_run(self._worker_num)
        self._shell.submit(self._print_output)
        self._shell.background_run(self._worker_num, self)
        asyncio.run(self._main())

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._stopped = True
        self._main_queue.put(None)
        self._console.print("start exiting")
        self._conversation.close()
        self._console.print("conversation closed")
        self._shell.close()
        self._console.print("ghostos shell shutdown")
        self._console.print("Exit, Bye!")
        exit(0)

    async def _main(self):
        self._welcome()
        self._console.print("waiting for agent say hi...")
        message = Role.new_system(
            self._welcome_user_message,
        )
        event, receiver = self._conversation.respond([message])
        self.output_receiver(receiver)

        with patch_stdout(raw=True):
            await self._loop()
            self._console.print("Quitting event loop. Bye.")

    def _print_output(self):
        while not self._stopped:
            try:
                message = self._main_queue.get(block=True)
                if message is None:
                    self.close()
                    return
                if not isinstance(message, Message):
                    raise ValueError(f"Expected Message, got {message}")
                self._print_message(message)
            except Empty:
                continue

    def output_receiver(self, receiver: Receiver):
        with self._thread_locker:
            status = Status("receiving", console=self._console)
            with status:
                with receiver:
                    buffer = None
                    for message in receiver.recv():
                        if self._stopped:
                            return

                        if message.is_complete():
                            buffer = None
                            self._main_queue.put(message)
                        elif buffer is None:
                            buffer = message.as_head()
                        else:
                            patched = buffer.patch(message)
                            if patched:
                                buffer = patched
                            else:
                                buffer = message.as_head()
                        if buffer:
                            status.update(buffer.content[-30:])
                        else:
                            status.update("")

    def output_event(self, event: Event):
        self._json_output(event.model_dump_json(indent=2, exclude_defaults=True))

    def on_error(self, error: Exception) -> bool:
        self._logger.exception(error)
        self.close()
        return False

    def on_event(self, event: Event, messages: List[Message]) -> None:
        self._logger.debug(f"Received event {event.event_id} for task {event.task_id}")
        # self.output_receiver(retriever)

    def alive(self) -> bool:
        return not self._stopped

    def halt(self) -> int:
        return 0

    async def _loop(self):
        session = self._prompt_session
        bindings = self._bindings()
        while not self._stopped:
            try:
                text = await session.prompt_async(multiline=False, key_bindings=bindings)
                if self._intercept_text(text):
                    continue
                self._console.print(Markdown("\n----\n"))
                self._on_input(text)
            except (EOFError, KeyboardInterrupt):
                self.close()
            except Exception:
                self._console.print_exception()
                self.close()

    def _on_input(self, text: str) -> None:
        """
        :return: task_id
        """
        message = Role.USER.new(
            content=text,
            name=self._username,
        )
        self._on_message_input(message)

    def _on_message_input(self, message: Message) -> None:
        """
        :return: task_id
        """
        event, receiver = self._conversation.respond([message])
        self.output_receiver(receiver)

    def _intercept_text(self, text: str) -> bool:
        if text == "/exit":
            self.close()
        return False

    @staticmethod
    def _bindings():
        bindings = KeyBindings()
        return bindings

    def _welcome(self) -> None:
        self._console.print(Markdown("""
----
# Console Demo

This demo provide a console interface to communicate with an agent. 

- print "/exit" to quit
----
"""))

    def _print_message(self, message: Message):
        if not message.is_complete():
            return

        if message.is_empty():
            return

        if not MessageType.is_text(message):
            self._console.print(
                Panel(
                    self._json_output(message.model_dump_json(exclude_defaults=True, indent=2)),
                    title="message debug",
                    border_style="green",
                )
            )
            return

        content = message.content
        # some message is not visible to user
        if not content:
            return
        payload = TaskPayload.read_payload(message)
        title = "receive message"
        # markdown content
        prefix = ""
        if payload is not None and self._debug:
            prefix = "\n>\n".join([
                f"> task_id: {payload.task_id}",
                f"> thread_id: {payload.thread_id}",
                f"> task_name: {payload.task_name}\n\n",
            ])

        markdown = self._markdown_output(prefix + content)
        # border style
        if MessageType.ERROR.match(message):
            border_style = "red"
        elif payload is not None and payload.task_id == self._main_task_id:
            border_style = "blue"
        else:
            border_style = "yellow"
            title = "receive async message"
        # print
        self._console.print(
            Panel(
                markdown,
                title=title,
                border_style=border_style,
            ),
        )

    @staticmethod
    def _json_output(json: str) -> Markdown:
        return Markdown(
            f"```python\n{json}\n```"
        )

    @staticmethod
    def _markdown_output(text: str) -> Markdown:
        return Markdown(text)
