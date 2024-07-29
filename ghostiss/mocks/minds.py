from ghostiss.core.ghosts import Operator
from ghostiss.core.ghosts.minds import Mindflow, MessageType
from ghostiss.mocks.operators import FakeOperator
from ghostiss.exports import Exporter


class FakeMindflow(Mindflow):
    def send(self, *messages: MessageType) -> None:
        print(*messages)

    def awaits(self, *questions: MessageType) -> Operator:
        return FakeOperator("FakeMindflow:awaits", *questions)

    def observe(self, *args, **kwargs) -> Operator:
        return FakeOperator("FakeMindflow:observe", *args, **kwargs)

    def finish(self, *results: MessageType) -> Operator:
        return FakeOperator("FakeMindflow:finish", results=results)

    def fail(self, *reasons: MessageType) -> Operator:
        return FakeOperator("FakeMindflow:fail", reasons=reasons)


EXPORTS = Exporter().with_attr("mindflow", FakeMindflow(), Mindflow)
