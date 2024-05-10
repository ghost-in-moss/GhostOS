from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import List, Dict, Iterator, Optional, Tuple, ClassVar
from pydantic import BaseModel, Field


class Package:
    def __init__(self, head: bool, finish: bool, content: str, memory: str = "",
                 payload: Optional[Dict] = None) -> None:
        self.head: bool = head
        self.finish: bool = finish
        self.content: str = content
        self.memory: str = memory
        self.payload: Optional[Dict] = payload
        self.update: bool = False

    @classmethod
    def header(cls, data: Dict) -> "Package":
        return cls(True, False, "", "", data)

    @classmethod
    def content(cls, content: str, memory: str = "", data: Optional[Dict] = None) -> "Package":
        return cls(False, False, "", memory, data)

    @classmethod
    def fin(cls) -> "Package":
        return cls(False, True, "", "", None)

    @classmethod
    def update(cls, content: str, memory: str = "", data: Optional[Dict] = None) -> "Package":
        return cls(False, False, content, memory, data)

    @classmethod
    def message(cls, data: Dict) -> "Package":
        return cls(True, True, "", "", data)


class Level(str, enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    NOTICE = "notice"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class Role(str, enum.Enum):
    """
    Role of who send this message
    """
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class Kind(str, enum.Enum):
    TEXT = "text"
    PYTHON = "python"


class Header(BaseModel):
    """
    message header
    """

    trace: str = Field(default="", description="Message trace")
    thread_id: str = Field(description="Message thread id")
    kind: str = Field(description="Message kind")


class Message(BaseModel):
    kind: str = Field(default=Kind.TEXT, description="Message kind")
    role: str = Field(description="Message role")
    name: str = Field(description="Message sender name")
    level: Optional[str] = Field(default=Level.INFO, description="Message level")
    done: bool = Field(default=True, description="if is streaming, done means it is last package")
    content: str = Field(default="", description="Message content")
    memory: str = Field(default="", description="Message as memory to the llm")
    additions: Optional[Dict[str, Dict]] = Field(default_factory=dict, description="Message additional information")

    # def buff(self, package: Package) -> None:
    #     if package.update:
    #         # 执行 update.
    #         self.update(package)
    #         return
    #
    #     if package.content:
    #         self.content = self.content + package.content
    #     if package.memory:
    #         self.memory = package.memory
    #     if package.payload is not None:
    #         self.payload = package.payload
    #
    # def update(self, package: Package) -> None:
    #     self.content = package.content
    #     self.memory = package.memory
    #     self.payload = package.payload


class Addition(ABC, BaseModel):
    key: ClassVar[str] = ""

    @classmethod
    def from_msg(cls, msg: Message) -> Optional[Addition]:
        if cls.key in msg.additional:
            return cls(**msg.additional[cls.key])
        return None


# class Message(BaseModel):
#     header: Header = Field(description="Message header")
#     body: Body = Field(default_factory=Body, description="Message body")
#
#     @classmethod
#     def from_package(cls, package: Package) -> Message | None:
#         if package.head:
#             return cls(header=package.payload,
#                        body=Body(content=package.content, memory=package.memory, payload=package.payload))
#         return None


class MessagesBuffer:

    def __init__(self) -> None:
        self.messages: List[Message] = []
        self.current: Optional[Message] = None
        self._done: bool = False

    def append(self, message: Message) -> None:
        if self._done:
            return
        self.messages.append(message)
        self.current = message

    def done(self):
        self._done = True

    def buff(self, package: Package) -> None:
        if self._done:
            return
        if package.finish:
            self.done()
            return

        if self.current is None:
            # 空历史, 检查首包.
            if not package.head:
                raise AttributeError("empty messages buffer receive package that is not head")

            message = Message.from_package(package)
            self.append(message)

        else:
            # 否则执行 buff.
            self.current.body.buff(package)


class Pipeline(ABC):
    """
    message pipeline that handling output messages
    """

    @abstractmethod
    def handle(self, message: Message) -> Iterator[Message]:
        pass


class Interceptor(ABC):
    """
    message interceptor that can intercept input message
    """

    def intercept(self, message: Message) -> Tuple[List[Message], bool]:
        pass


class Messenger(ABC):
    """
    消息的传递模块.
    需要支持各种消息的传递方式. 常见的有:
    1. 同步整体返回
    2. 同步流式 (多模态, 可扩展) 返回.
    """

    @abstractmethod
    def packages(self) -> Iterator[Package]:
        """
        return atomic packages
        """
        pass

    @abstractmethod
    def messages(self) -> Iterator[Message]:
        """
        return joined messages
        """
        pass
