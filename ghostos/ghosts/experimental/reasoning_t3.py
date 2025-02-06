from ghostos.abcd import Session, Thought, ActionThought, ChainOfThoughts
from ghostos.ghosts.chatbot import Chatbot, ChatbotDriver
from ghostos.thoughts.meta_prompt_experiments import MetaPromptExp3


class ReasoningChatbotT3(Chatbot):
    pass


class ReasoningChatbotT3Driver(ChatbotDriver):

    def __init__(self, ghost: ReasoningChatbotT3):
        super().__init__(ghost)

    def thought(self, session: Session) -> Thought:
        return ChainOfThoughts(
            final=ActionThought(
                llm_api=self.ghost.llm_api,
                actions=self.actions(session),
            ),
            chain=[
                MetaPromptExp3(
                    llm_api_name=self.ghost.llm_api,
                ),
            ]
        )
