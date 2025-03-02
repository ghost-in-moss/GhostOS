from typing import Union

from ghostos.abcd import Operator, Session
from ghostos.libraries.thinking.abcd import Reasoning
from ghostos.core.llms import LLMs
from ghostos.core.messages import Role, MessageStage


class SyncReasoningOperator(Operator):

    def __init__(self, instruction: str, llm_api: str = ""):
        self.instruction = instruction
        self.llm_api = llm_api

    def run(self, session: Session) -> Union[Operator, None]:
        thread = session.get_truncated_thread()
        fork = thread.fork()
        llms = session.container.force_fetch(LLMs)
        llm_api = llms.get_api(self.llm_api)
        instruction = session.get_system_instructions()
        systems = []
        if instruction:
            systems.append(Role.new_system(content=instruction))
        prompt = fork.to_prompt(
            system=systems,
            stages=None,
            truncate=True,
        )
        messenger = session.messenger(stage=MessageStage.REASONING)
        items = llm_api.deliver_chat_completion(prompt, not messenger.completes_only())
        messenger.send(items)
        messages, callers = messenger.flush()
        session.thread.append(*messages)

        return session.mindflow().think(sync=True)

    def destroy(self):
        pass


class ReasoningImpl(Reasoning):

    def __init__(self, session: Session):
        self._session = session

    def reasoning(self, instruction: str) -> Operator:
        return SyncReasoningOperator(instruction)

    def async_reasoning(self, instruction: str = "") -> Operator:
        pass
