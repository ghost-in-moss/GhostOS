from ghostos.ghosts.experimental.reasoning_t2 import ReasoningChatbotT2

__ghost__ = ReasoningChatbotT2(
    id=__name__,
    name="jojo",
    description="a chatbot for baseline test",
    persona="you are an LLM-driven cute girl, named jojo",
    instruction="remember talk to user with user's language."
)
