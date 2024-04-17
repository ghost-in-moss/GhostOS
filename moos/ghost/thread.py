from .message import History


class Thread:
    history: History  # chat history
    variables: dict[str, str]
