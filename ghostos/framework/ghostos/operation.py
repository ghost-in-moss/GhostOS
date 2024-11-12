from __future__ import annotations

from ghostos.core.abcd import Operator
from ghostos.core.abcd.concepts import Operation, Session
from ghostos.core.messages import MessageKind, MessageKindParser


class OperationImpl(Operation):

    def __init__(self, parser: MessageKindParser, session: Session):
        self.session = session
        self.parser = parser

    def finish(self, status: str = "", *replies: MessageKind) -> Operator:
        pass

    def fail(self, status: str = "", *replies: MessageKind) -> Operator:
        pass

    def wait(self, status: str = "", *replies: MessageKind) -> Operator:
        pass

    def observe(self, *messages: MessageKind) -> Operator:
        pass

    def on_error(self, *messages: MessageKind) -> Operator:
        pass
