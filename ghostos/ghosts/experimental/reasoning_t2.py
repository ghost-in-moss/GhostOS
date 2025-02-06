from ghostos.abcd import Session, Thought, ActionThought, ChainOfThoughts
from ghostos.ghosts.chatbot import Chatbot, ChatbotDriver
from ghostos.thoughts.meta_prompt_experiments import MetaPromptExp2


class ReasoningChatbotT2(Chatbot):
    pass


class ReasoningChatbotT2Driver(ChatbotDriver):

    def __init__(self, ghost: ReasoningChatbotT2):
        super().__init__(ghost)

    def thought(self, session: Session) -> Thought:
        return ChainOfThoughts(
            final=ActionThought(
                llm_api=self.ghost.llm_api,
                actions=self.actions(session),
            ),
            chain=[
                MetaPromptExp2(
                    llm_api_name=self.ghost.llm_api,
                ),
            ]
        )
