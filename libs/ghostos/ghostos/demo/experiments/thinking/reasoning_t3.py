from ghostos.ghosts.experimental.reasoning_t3 import ReasoningChatbotT3

__ghost__ = ReasoningChatbotT3(
    id=__name__,
    name="jojo",
    description="a chatbot for baseline test",
    persona="you are an LLM-driven cute girl, named jojo",
    instruction="remember talk to user with user's language.",
    llm_api="gpt-4-turbo",
)
