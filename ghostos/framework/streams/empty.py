from ghostos.core.messages import Stream, Message


class EmptyStream(Stream):
    """
    for mock or test
    """

    def deliver(self, pack: "Message") -> bool:
        return True

    def accept_chunks(self) -> bool:
        return False

    def stopped(self) -> bool:
        return False

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
