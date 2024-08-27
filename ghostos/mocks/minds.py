from ghostos.core.ghosts import Operator
from ghostos.core.ghosts.schedulers import Taskflow, MessageKind, MultiTask
from ghostos.core.ghosts.thoughts import Thought
from ghostos.mocks.operators import FakeOperator
from ghostos.core.moss_p1.exports import Exporter


class FakeTaskflow(Taskflow):
    def send(self, *messages: MessageKind) -> None:
        print(*messages)

    def awaits(self, *replies: MessageKind) -> Operator:
        return FakeOperator("FakeMindflow:awaits", *replies)

    def observe(self, *args, **kwargs) -> Operator:
        return FakeOperator("FakeMindflow:observe", *args, **kwargs)

    def finish(self, *results: MessageKind) -> Operator:
        return FakeOperator("FakeMindflow:finish", results=results)

    def fail(self, *reasons: MessageKind) -> Operator:
        return FakeOperator("FakeMindflow:fail", reasons=reasons)


class FakeMultiTask(MultiTask):

    def wait_on_tasks(self, *thoughts: Thought) -> Operator:
        pass

    def run_tasks(self, *thoughts: Thought) -> None:
        pass

    def send_task(self, task_name: str, *messages: MessageKind) -> None:
        pass

    def cancel_task(self, name: str, reason: str) -> None:
        pass


EXPORTS = Exporter(). \
    attr("mindflow", FakeTaskflow(), Taskflow).\
    attr("multi_tasks", FakeMultiTask(), MultiTask)

