from ghostiss.core.ghosts import Operator
from ghostiss.core.ghosts.minds import Mindflow, MessageType, MultiTasks
from ghostiss.core.ghosts.thoughts import Thought
from ghostiss.mocks.operators import FakeOperator
from ghostiss.core.moss.exports import Exporter


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


class FakeMultiTasks(MultiTasks):

    def wait_on_tasks(self, *thoughts: Thought) -> Operator:
        pass

    def run_tasks(self, *thoughts: Thought) -> None:
        pass

    def send_task(self, task_name: str, *messages: MessageType) -> None:
        pass

    def cancel_task(self, name: str, reason: str) -> None:
        pass


EXPORTS = Exporter(). \
    attr("mindflow", FakeMindflow(), Mindflow).\
    attr("multi_tasks", FakeMultiTasks(), MultiTasks)

