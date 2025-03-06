from typing import List, Dict, Optional, Union
from typing_extensions import Literal, Self
from pydantic import BaseModel, Field

from ghostos.abcd import Operator, Session
from ghostos.libraries.planner.abcd import Planner
from ghostos_common.helpers import generate_import_path


class TaskInfo(BaseModel):
    name: str = Field(description="task name")
    description: str = Field(description="task description")
    steps: List[str] = Field(description="task steps")
    at: int = Field(default=0, description="task at step index")
    state: Literal["running", "canceled", "finished", "pending"] = Field("pending", description="task state")
    done: Dict[str, bool] = Field(default_factory=dict, description="task done")


class Tasks(BaseModel):
    tasks: Dict[str, TaskInfo] = Field(default_factory=dict)
    current: Optional[str] = Field(default=None, description="current task")


class PlannerImpl(Planner):

    def __init__(self, session: Session):
        self.key = generate_import_path(Planner)
        if self.key not in session.state:
            session.state[self.key] = Tasks()
        data = session.state[self.key]
        if not isinstance(data, Tasks):
            data = Tasks()
        self.data: Tasks = data
        self.session = session
        self.session.state[self.key] = data

    def save_task(self, name: str, desc: str, steps: List[str]) -> None:
        task = TaskInfo(name=name, description=desc, steps=steps)
        self.data.tasks[name] = task
        return None

    def next(self, task_name: Union[str, None] = None, *, wait: bool = False) -> Operator:
        if task_name is None:
            task_name = self.data.current
        if not task_name:
            return self.session.mindflow().error(f"task {task_name} not found")
        task = self.data.tasks[task_name]
        if task.at >= len(self.data.steps):
            task.state = "finished"
            return self.session.mindflow().wait()
        task.at += 1
        # todo.
        step = task.steps[task.at]
        return self.session.mindflow().think()

    def cancel(self, task_name: Union[str, None] = None) -> Operator:
        pass
