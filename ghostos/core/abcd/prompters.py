from .concepts import Prompter
from ghostos.container import Container
from pydantic import Field


class SystemPrompter(Prompter):
    """
    root of the prompt
    """
    meta_prompt: str = Field(
        default="",
        description="meta prompt for agent",
    )

    def self_prompt(self, container: Container, depth: int = 0) -> str:
        return self.meta_prompt
