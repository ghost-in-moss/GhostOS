from __future__ import annotations

import enum
import json
import uuid
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Iterator, Optional, Tuple, ClassVar, Any
from pydantic import BaseModel, Field


class Level(str, enum.Enum):
    """
    todo: level 可能去掉.
    """
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
    # 文本类型的消息.
    TEXT = "text"
    # 需要用 python 引擎执行的代码.
    PYTHON = "python"
    # 调用了一个 function
    REACTION_CALL = "reaction_call"
    REACTION_CALLBACK = "reaction_callback"


class Header(BaseModel):
    """
    消息头.
    """

    msg_id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    created: int = Field(default_factory=lambda: int(time.time()), description="Message creation time")
    level: str = Field(default="", description="Message level")
    kind: str = Field(default="", description="Message kind")
    role: str = Field(default="", description="Message role")
    name: str = Field(default="", description="Message sender name")

    def new(self) -> "Message":
        return Message(header=self)


class Message(BaseModel):
    """
    通用的 message 协议.
    在支持流式传输的基础上, 允许使用 attachments 添加弱类型的数据信息.
    """

    header: Header = Field(description="message header")
    content: str = Field(default="", description="Message content")
    memory: str = Field(default="", description="Message as memory to the llm")
    attachments: Optional[Dict[str, Dict[str, Any]]] = Field(default=None, description="Message additional information")

    def get_memory(self) -> str:
        if self.memory:
            return self.memory
        return self.content

    def get_level(self) -> str:
        if not self.level:
            return Level.INFO
        # todo: 去掉不合法的.
        return self.level

    def update(self, message: Message, reset: bool = False) -> bool:
        if message.header:
            return False

        # update content
        if message.content:
            if reset:
                self.content = message.content
            else:
                self.content = self.content + message.content
        # update memory
        if message.memory:
            self.memory = message.memory
        # update attachments
        if message.attachments is not None and not reset:
            for key, value in message.attachments.items():
                self.attachments[key] = value
        elif message.attachments is not None and reset:
            self.attachments = message.attachments
        return True


class Attachment(ABC, BaseModel):
    """
    message attachment
    """

    attach_key: ClassVar[str] = ""

    @classmethod
    def retrieve(cls, msg: Message) -> Optional[Attachment]:
        """
        retrieve attachment from message
        """
        if cls.attach_key in msg.attachments:
            return cls(**msg.attachments[cls.attach_key])
        return None

    def set(self, msg: Message) -> None:
        """
        set attachment to message
        """
        msg.attachments[self.attach_key] = self.model_dump()


class Package(Message):
    done: bool = Field(description="")
    final: bool = Field(description="")

    @classmethod
    def new_header(cls, header: Header) -> "Package":
        return cls(header=header, first=True)

    @classmethod
    def new_content(cls, data: Dict) -> "Package":
        data["done"] = False
        data["final"] = False
        return cls(**data)

    @classmethod
    def new_tail(cls, data: Dict) -> "Package":
        data["done"] = True
        data["final"] = False
        return cls(**data)

    @classmethod
    def new_final(cls) -> "Package":
        return cls(final=True)

    @classmethod
    def new_msg(cls, data: Dict) -> "Package":
        data["done"] = True
        data["final"] = False
        return cls(**data)

    # @classmethod
    # def new_pack(cls, content: str, memory: str = "", additions: Optional[Dict[str, Dict]] = None) -> Message:
    #     """
    #
    #     """
    #     return cls(content=content, memory=memory, additions=additions)
    #
    # @classmethod
    # def first_pack(cls, header: Header) -> Message:
    #     return cls(header=header)
    #
    # @classmethod
    # def final_pack(cls, reset: Optional[Dict] = None) -> Message:
    #     if reset:
    #         data = reset
    #     else:
    #         data = {}
    #     data["finish"] = True
    #     return cls(**data)
#
#
# class MsgChoices(Attachment):
#     """
#     单选的选项.
#     """
#     property_name = "suggestions"
#     choices: List[str] = Field(default_factory=list)
#
#
# class MsgSelections(Attachment):
#     """
#     多选的消息. 输入, 输出消息都可以包含多选的选项.
#     """
#     property_name = "selections"
#     choices: List[str] = Field(default_factory=list)
#
#
# class MsgFile(Attachment):
#     """
#     文件的封装.
#     """
#     property_name = "file"
#
#     file_id: str = Field(default="", description="File id")
#     file_name: str = Field(default="", description="File name")
#     url: str = Field(default="", description="File url")
#     desc: str = Field(default="", description="File description")


class Pipe(ABC):
    """
    message pipeline that handling output messages
    """

    @abstractmethod
    def handle(self, message: Message) -> Iterator[Message]:
        pass


class Pipeline:
    """
    流式 pipeline 的一个极简实现.
    """

    def __init__(self, *pipes: Pipe):
        self.pipes = list(pipes)

    def parse(self, message: Message) -> Iterator[Message]:
        for unpack in self._parse(message, self.pipes.copy()):
            yield unpack

    def _parse(self, package: Message, pipes: List[Pipe]) -> Iterator[Message]:
        if not pipes:
            yield package
        else:
            pipe = pipes.pop()
            for package in self._parse(package, *pipes):
                for handled in pipe.handle(package):
                    yield handled


class Interceptor(ABC):
    """
    message interceptor that can intercept input message
    """

    def intercept(self, message: Message) -> Tuple[List[Message], bool]:
        pass


class Output(ABC):

    def send(self, package: Message) -> None:
        pass


class Retriever(ABC):
    """
    拉取消息.
    """

    @abstractmethod
    def read_package(self) -> Iterator[Message]:
        """
        return streaming message package
        """
        pass

    @abstractmethod
    def done(self) -> bool:
        pass

    @abstractmethod
    def wait(self) -> Iterator[Message]:
        """
        wait to get all packed message
        """
        pass


class Stream(ABC):
    @abstractmethod
    def output(self) -> Output:
        pass

    @abstractmethod
    def retriever(self) -> Retriever:
        pass

# class MessageBuffer(ABC):
#
#     @abstractmethod
#     def buff(self, package: Message) -> Iterator[Message]:
#         """
#         尝试缓冲一个 package, 进行粘包等操作.
#         返回这一轮需要发送的包, 和完成粘包的包.
#         有可能产生多个待发送的包.
#         """
#         pass
#
#     @abstractmethod
#     def pop(self) -> Optional[Message]:
#         """
#         吐出一个经过 buff, 已经完成了 buff 的消息体.
#         """
#         pass
#
#     @abstractmethod
#     def buffer(self) -> List[Message]:
#         pass
#
#     @abstractmethod
#     def clear(self) -> MessageBuffer:
#         """
#         清空 buffer 并返回.
#         """
#         pass


# class Messenger(ABC):
#
#     @abstractmethod
#     def new(
#             self,
#             buffer: Optional[MessageBuffer] = None,
#             deliver: bool = True,
#             *pipeline: Pipe,
#     ) -> Messenger:
#         """
#         清除所有的缓存.
#         """
#         pass
#
#     @abstractmethod
#     def retrieve(self, msg_id: str) -> Optional[Message]:
#         """
#         读取一个完整的 msg
#         """
#         pass
#
#     @abstractmethod
#     def parse(self, *messages: Message) -> Iterator[Message]:
#         """
#         将消息协议处理和转换的能力.
#         """
#         pass
#
#     @abstractmethod
#     def send(self, *messages: Message) -> Messenger:
#         """
#         发送消息体到端上.
#         """
#         pass
#
#     @abstractmethod
#     def wait(self) -> List[Message]:
#         """
#         :return: buffed messages
#         """
#         pass
