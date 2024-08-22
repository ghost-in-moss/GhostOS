from typing import Any, Optional, Dict

from ghostiss.core.moss import MossCompiler
from ghostiss.core.quests.itf import QuestContext, QuestLib, QuestOperator, Quest
from ghostiss.core.quests.utils import get_quest_driver
from ghostiss.core.quests.steps import ObserveOperator, FinishOperator
from ghostiss.contracts.modules import Modules
from ghostiss.contracts.logger import LoggerItf
from ghostiss.container import Container, provide
from ghostiss.core.session import Messenger
from ghostiss.core.messages import Role


class QuestContextImpl(QuestContext):
    """
    一个简单的实现.
    """

    def __init__(self, container: Container, parent: QuestLib, messenger: Messenger, max_step: int, depth: int = 0):
        self._modules: Modules = container.force_fetch(Modules)
        self._container = Container(parent=container)
        self._container.set(QuestLib, self)
        self._parent = parent
        self._messenger = messenger
        self._logger = container.force_fetch(LoggerItf)
        self._sub_context = []
        self._values = {}
        self._result: Any = None
        self._max_step = max_step
        self._depth = depth

    def container(self) -> Container:
        return self._container

    def execute(self, quest: Quest) -> Any:
        """
        QuestContext 运行一个任务, 并返回结果.
        :param quest:
        :return:
        """
        driver = get_quest_driver(quest.__class__)
        instance = driver(quest)

        thread = instance.init()
        thread, step = instance.run(self.container(), self.messenger(), thread)
        count = 1
        while step is not None:
            if count > self._max_step:
                raise RuntimeError(f"Max step {self._max_step} reached")
            # todo: log
            thread, step = step.next(self, instance, thread)
            instance.on_save(self.container(), thread)
            count += 1
        # 预计运行过程中, result 已经通过 set_result 或者 finish 进行赋值了.
        return self._result

    def messenger(self) -> Messenger:
        return self._messenger

    def sub_context(self) -> "QuestContext":
        ctx = QuestContextImpl(
            container=self._container,
            parent=self,
            messenger=self._messenger.new(),
            max_step=self._max_step,
            depth=self._depth + 1,
        )
        self._sub_context.append(ctx)
        return ctx

    def set_result(self, result: Any) -> None:
        self._result = result

    def values(self) -> Dict[str, Any]:
        return self._values

    def run(self, key: str, quest: Quest) -> Any:
        # 关键逻辑, 每次运行的时候, 实际上为 quest 生成了一个 sub context
        sub_context = self.sub_context()
        result = sub_context.execute(quest)
        self._values[key] = result
        return result

    def get(self, key: str) -> Optional[Any]:
        return self._values.get(key, None)

    def set(self, key: str, value: Any):
        self._values[key] = value

    def observe(self, **kwargs) -> QuestOperator:
        content = "observe values: \n\n"
        lines = []
        for key, value in kwargs.items():
            line = f"## `{key}`\n\n{value}"
            lines.append(line)
        content = content + "\n\n".join(lines)
        message = Role.SYSTEM.new(content=content)
        return ObserveOperator([message])

    def finish(self, result: Any) -> QuestOperator:
        return FinishOperator(result)

    def destroy(self) -> None:
        for sub_context in self._sub_context:
            sub_context.destroy()
        del self._sub_context
        self._container.destroy()
        del self._container
        del self._values
        del self._logger
        del self._result
        del self._modules
