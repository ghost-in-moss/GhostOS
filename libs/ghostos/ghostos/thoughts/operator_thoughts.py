from typing import Tuple, Optional

from ghostos.abcd import OpThought, Session, Operator
from pydantic import BaseModel, Field

from ghostos.core.llms import Prompt, LLMs
from ghostos.core.messages import Role, MessageStage
from ghostos.core.runtime import EventTypes


class NoticesThought(BaseModel, OpThought):
    """
    add notices before next thought.
    """
    notices: str = Field(
        description="the notice put before action",
    )

    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[Operator]]:
        notices = Role.new_system(content=f"Notices before your actions:\n {self.notices}")
        prompt.added.append(notices)
        return prompt, None


class SelfQuestionThought(BaseModel, OpThought):
    """
    level 1 reasoning: generate `reasoning instruction` for action thoughts.
    """

    question: str = Field(description="the question ask your self")
    llm_api_name: str = Field(default="", description="llm api name")

    def get_meta_prompt(self) -> str:
        return f"""
你现在在思考模式, 接下来的输出是思考内容, 只有你自己可以看到, 指导你采取正确的行动.
所以你需要用 "我" 作为主语思考.  
你需要思考并回答以下问题: 

{self.question}
"""

    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[Operator]]:
        thread = session.thread
        event = thread.last_turn().event
        if not event or event.type != EventTypes.INPUT.value:
            return prompt, None
        _prompt = prompt.model_copy(deep=True)
        _reasoning = []
        instruction = Role.new_system(content=self.get_meta_prompt())
        instruction.stage = MessageStage.REASONING.value
        _prompt.added.append(instruction)

        messenger = session.messenger(stage=MessageStage.REASONING.value)
        llm_api = session.container.force_fetch(LLMs).get_api(self.llm_api_name)
        items = llm_api.deliver_chat_completion(_prompt, not messenger.completes_only())
        messenger.send(items)
        messages, _ = messenger.flush()
        if len(messages) > 0:
            session.logger.debug("reasoning thoughts: %s", messages[-1].get_content())

        # update response to origin prompt
        thread.append(*_reasoning)
        prompt.added.extend(_reasoning)
        return prompt, None
