class SessionError(RuntimeError):
    """
    Session level exception, which is able to recovery
    """
    pass


class StreamingError(RuntimeError):
    pass


class ConversationError(RuntimeError):
    """
    Conversation level exception, conversation shall be closed
    """
    pass
