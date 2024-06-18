from typing import ClassVar, Union, Set, List, Iterable, Dict, Any
from abc import ABC, abstractmethod
from enum import Enum
from ghostiss.entity import BaseEntityClass
from pydantic import BaseModel, Field
from openai.types.chat import (
    chat_completion_system_message_param,
    chat_completion_user_message_param,
    chat_completion_assistant_message_param,
    chat_completion_function_message_param,
    chat_completion_content_part_image_param,
    chat_completion_content_part_text_param,
    chat_completion_role,

)

OPENAI_MESSAGE_TYPES = Union[
    chat_completion_system_message_param.ChatCompletionSystemMessageParam,
    chat_completion_user_message_param.ChatCompletionUserMessageParam,
    chat_completion_assistant_message_param.ChatCompletionAssistantMessageParam,
    chat_completion_function_message_param.ChatCompletionFunctionMessageParam,
]
""" openai 的 message 封装真烂, 走多态路线. """


class OpenAIMsgKind(str, Enum):
    TEXT = "text"
    # STREAM_TEXT = "stream_texts"
    IMAGES = "images"
    # STREAM_IMAGES = "stream_images"
    TEXTS = "texts"


class OpenAIMsgRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"
    TOOL = "tool"

    @classmethod
    def all(cls) -> Set[str]:
        return {cls.SYSTEM, cls.USER, cls.ASSISTANT, cls.FUNCTION, cls.TOOL}


class OpenAIMsg(BaseEntityClass, ABC):
    kind: ClassVar[str]

    @classmethod
    def entity_kind(cls) -> str:
        pass

    def entity_id(self) -> str:
        return ""

    @abstractmethod
    def to_openai_msg(self) -> OPENAI_MESSAGE_TYPES:
        pass


class Text(OpenAIMsg):
    kind: ClassVar[str] = OpenAIMsgKind.TEXT

    role: str = Field(description="role", enum=OpenAIMsgRole.all())
    content: str = Field(description="content")
    name: str = Field(default="", description="name")

    def to_openai_msg(self) -> OPENAI_MESSAGE_TYPES:
        if self.role == OpenAIMsgRole.USER:
            return chat_completion_user_message_param.ChatCompletionUserMessageParam(
                content=self.content, name=self.name, role="user",
            )
        elif self.role == OpenAIMsgRole.SYSTEM:
            return chat_completion_system_message_param.ChatCompletionSystemMessageParam(
                content=self.content, name=self.name, role="system",
            )
        elif self.role == OpenAIMsgRole.ASSISTANT:
            return chat_completion_assistant_message_param.ChatCompletionAssistantMessageParam(
                content=self.content, name=self.name, role="assistant",
            )
        elif self.role == OpenAIMsgRole.FUNCTION:
            return chat_completion_function_message_param.ChatCompletionFunctionMessageParam(
                content=self.content, name=self.name, role="function",
            )
        else:
            raise ValueError(f"Unsupported role: {self.role}")


class ImageUrl(BaseModel):
    url: str = Field(description="Either a URL of the image or the base64 encoded image data.")
    detail: str = Field(
        enum={"auto", "low", "high"},
        description="""
Specifies the detail level of the image.
Learn more in the
[Vision guide](https://platform.openai.com/docs/guides/vision/low-or-high-fidelity-image-understanding).""",
    )

    def to_openai_msg(
            self,
    ) -> chat_completion_content_part_image_param.ChatCompletionContentPartImageParam:
        return chat_completion_content_part_image_param.ChatCompletionContentPartImageParam(
            image_url=self.model_dump(),
            type="image_url"
        )


class Images(OpenAIMsg):
    kind: ClassVar[str] = OpenAIMsgKind.IMAGES
    role: str = Field(default="user", const=OpenAIMsgRole.USER)
    images: List[ImageUrl] = Field(description="images")

    def _get_content(self) -> List[chat_completion_content_part_image_param.ChatCompletionContentPartImageParam]:
        result = []
        for image in self.images:
            part = chat_completion_content_part_image_param.ChatCompletionContentPartImageParam(
                image_url=image.model_dump(),
                type="image_url",
            )
            result.append(part)
        return result

    def to_openai_msg(self) -> OPENAI_MESSAGE_TYPES:
        if self.role == OpenAIMsgRole.USER:
            return chat_completion_user_message_param.ChatCompletionUserMessageParam(
                content=self._get_content(), name=self.name, role="user",
            )
        raise ValueError(f"Unsupported role: {self.role}")


class Texts(OpenAIMsg):
    kind: ClassVar[str] = OpenAIMsgKind.TEXTS
    role: str = Field(default="user", const=OpenAIMsgRole.USER)
    parts: List[str] = Field(description="parts")

    def to_openai_msg(self) -> OPENAI_MESSAGE_TYPES:
        if self.role == OpenAIMsgRole.USER:
            return chat_completion_user_message_param.ChatCompletionUserMessageParam(
                content=self._get_content(), name=self.name, role="user",
            )
        raise ValueError(f"Unsupported role: {self.role}")

    def _get_content(self) -> List[chat_completion_content_part_text_param.ChatCompletionContentPartTextParam]:
        result = []
        for line in self.parts:
            part = chat_completion_content_part_text_param.ChatCompletionContentPartTextParam(
                text=line,
                type="text",
            )
            result.append(part)
        return result

# class StreamImages(OpenAIMsg):
#     """
#     流式输入的图片. 不过还是输入 url. 因为 openai 会要求先上传...
#     """
#     kind: ClassVar[str] = OpenAIMsgKind.STREAM_IMAGES
#     msg_id: str = Field(description="message id")
#
#     def to_openai_msg(self, retriever: MsgRetriever) -> OPENAI_MESSAGE_TYPES:
#         if self.role == OpenAIMsgRole.USER:
#             iterator = self._read_images(retriever)
#             return chat_completion_user_message_param.ChatCompletionUserMessageParam(
#                 content=iterator, name=self.name, role="user",
#             )
#         raise ValueError(f"Unsupported role: {self.role}")
#
#     def _read_images(
#             self,
#             retriever: MsgRetriever,
#     ) -> Iterable[chat_completion_content_part_image_param.ChatCompletionContentPartImageParam]:
#         for data in retriever.read(self.msg_id):
#             image = ImageUrl(**data)
#             yield image.to_openai_msg()


# class TextPart(BaseModel):
#     text: str = Field(description="text")
#
#     def to_openai_msg(
#             self,
#     ) -> chat_completion_content_part_text_param.ChatCompletionContentPartTextParam:
#         return chat_completion_content_part_text_param.ChatCompletionContentPartTextParam(
#             text=self.text,
#             type="text",
#         )


# class StreamTexts(OpenAIMsg):
#     """
#     流式输入的 texts
#     """
#
#     kind: ClassVar[str] = OpenAIMsgKind.STREAM_TEXT
#     msg_id: str = Field(description="message id")
#     name: str = Field(default="", description="name")
#     parts: List[str] = Field(description="parts")
#
#     def to_openai_msg(self, retriever: MsgRetriever) -> OPENAI_MESSAGE_TYPES:
#         iterator = self._read_texts(retriever)
#         if self.role == OpenAIMsgRole.USER:
#             return chat_completion_user_message_param.ChatCompletionUserMessageParam(
#                 content=iterator, name=self.name, role="user",
#             )
#         raise ValueError(f"Unsupported role: {self.role}")
#
#     def _read_texts(
#             self,
#             retriever: MsgRetriever,
#     ) -> Iterable[chat_completion_content_part_text_param.ChatCompletionContentPartTextParam]:
#         for data in retriever.read(self.msg_id):
#             text = TextPart(**data)
#             yield text.to_openai_msg()
