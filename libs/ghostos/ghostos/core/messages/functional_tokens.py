from typing import Iterable, List, Optional, Tuple
from typing_extensions import Self
from ghostos.core.messages.pipeline import Pipe
from ghostos.core.messages.message import Message, MessageType
from ghostos.core.llms.tools import FunctionalToken
from pydantic import BaseModel, Field

__all__ = ["XMLFunctionalTokenPipe"]


class XMLFunctionalTokenPipe(Pipe):
    """
    with functional token parse Text Message and generate caller from xml functional tokens.
    """

    class FunctionalTokenParsed(BaseModel):
        token: Optional[FunctionalToken] = Field(default=None)
        full_content: str = Field(default="")
        arguments: str = Field(default="")

    def __init__(
            self,
            functional_tokens: List[FunctionalToken],
            stages: Optional[List[str]] = None
    ):
        self.functional_tokens = functional_tokens
        if stages is None:
            stages = ['']
        self.stages = set(stages)

    def new(self) -> Self:
        return self

    def across(self, messages: Iterable[Message]) -> Iterable[Message]:
        if len(self.functional_tokens) == 0:
            yield from messages
            return

        for item in messages:
            if not item.is_complete():
                yield item
                continue
            if not MessageType.is_text(item):
                yield item
                continue
            if item.stage not in self.stages:
                yield item
                continue

            output_item = item.get_copy()
            parsed = self._parse_functional_token_of_message(item.content)
            memory = ""
            content = ""
            callers = []
            for parsed_item in parsed:
                if parsed_item.token is None:
                    # 正常内容.
                    memory += parsed_item.full_content
                    content += parsed_item.full_content
                else:
                    # matched functional token
                    # add caller first
                    caller = parsed_item.token.new_caller(parsed_item.arguments)
                    callers.append(caller)

                    memory += parsed_item.full_content
                    if parsed_item.token.visible:
                        content += parsed_item.full_content

            output_item.callers = callers
            output_item.content = content
            if memory != content:
                output_item.memory = memory
            yield output_item

    def _parse_functional_token_of_message(self, content: str) -> Iterable[FunctionalTokenParsed]:
        """
        做一个非常简单的函数实现, 将字符串按 xml token 的方式拆分.
        """
        left_content = content
        for ft in self.functional_tokens:
            matched, before, arguments, after = self._parse_content_with_xml_token(left_content, ft.token)
            if not matched:
                # continue with other tokens.
                continue

            yield self.FunctionalTokenParsed(
                token=None,
                full_content=before,
            )
            yield self.FunctionalTokenParsed(
                token=ft,
                arguments=arguments,
                full_content=f"<{ft.token}>{arguments}</{ft.token}>",
            )
            left_content = after
            if not left_content:
                break

        if left_content:
            yield self.FunctionalTokenParsed(
                token=None,
                full_content=left_content,
            )

    _Before = str
    _Arguments = str
    _After = str

    @staticmethod
    def _parse_content_with_xml_token(content: str, token: str) -> Tuple[bool, _Before, _Arguments, _After]:
        start_mark = f"<{token}>"
        end_mark = f"</{token}>"
        parts = content.split(start_mark)
        if len(parts) < 2:
            return False, content, "", ""
        before = parts[0]
        arguments = start_mark.join(parts[1:])
        parts = arguments.split(end_mark)
        if len(parts) < 2:
            return False, content, "", ""
        else:
            return True, before, parts[0], end_mark.join(parts[1:])
