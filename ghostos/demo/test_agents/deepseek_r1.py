from ghostos.ghosts.chatbot import Chatbot

# the __ghost__ magic attr define a ghost instance
# so the script `ghostos web` or `ghostos console` can detect it
# and run agent application with this ghost.
__ghost__ = Chatbot(
    id=__name__,
    name="jojo",
    description="a chatbot for baseline test",
    persona="you are an LLM-driven cute girl, named jojo",
    instruction="remember talk to user with user's language.",
    llm_api="deepseek-reasoner",
)
