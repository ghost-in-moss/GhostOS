from ghostos.ghosts.chatbot import Chatbot

# the __ghost__ magic attr define a ghost instance
# so the script `ghostos web` or `ghostos console` can detect it
# and run agent application with this ghost.
__ghost__ = Chatbot(
    name="translator",
    description="a chatbot that translate only",
    persona="you are an translator",
    instruction="translate user's input into english, do nothing else.",
    llm_api="moonshot-v1-32k",
    history_turns=0,
)
