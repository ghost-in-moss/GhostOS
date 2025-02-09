from typing import List, Dict
from typing_extensions import Literal
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class PlanNode(BaseModel):
    name: str = Field(description="simple short name for a node")
    instruction: str = Field(description="the instruction of this node")
    current: int = Field(description="the current step index")
    steps: List[str] = Field(
        default_factory=list,

    )


class Plan(BaseModel):
    name: str = Field(description="the name of a plan")
    desc: str = Field(description="the description of the plan")
    state: Literal["running", "pending", "waiting", "aborted", "done", "canceled"] = Field(
        default="running", description="state of node"
    )
    current: str = Field(default="", description="current node name")

    nodes: List[PlanNode] = Field(default_factory=list, description="the planned nodes")
    edges: Dict[str, List[str]] = Field(default_factory=dict, description="the edges of the nodes")

    updated_turn: int = Field(default=0, description="the last turns update the plan")


class Planning(BaseModel):
    plans: List[Plan] = Field(default_factory=list, description="the planned nodes")
    current: str = Field(default="", description="the current plan name")
    turns: int = Field(default=0, description="the plan counting turns")
    max: int = Field(default=0, description="the max plans")


class Planner(ABC):
    """
    Planner 是给你提供用来做长程任务规划的记事本.
    当一件事你无法在一轮交互内完成, 而需要多轮交互, 和动态规划时, 你可以用 planner 记录你的规划.
    而 Planner 在每一轮中都会告知你当前上下文所处的规划位置, 帮助你聚焦于当前的任务, 同时避免分神或遗忘.

    Planner 的设计思路如下:
    1. 支持创建多个任务, 可以根据场景的需要, 主动在任务之间切换. 切换的函数是 switch_to
    2. 每个任务在多个状态中切换: 取消(cancel)/完成(done)/放弃(abort)/搁置(pending)/执行中(running)
    3. 每个任务由 1 ~ n 个 `节点` 构成, 节点之间可连线成图.
    4. 每个节点内部由 1 ~ n 个顺序 step 构成.
    5. 每个节点和节点的每个步骤默认都需要一轮独立的交互, 切换节点的核心函数是 goto, 切换步骤的核心函数是 next
    6. 结束的任务会被垃圾回收.
    """

    @abstractmethod
    def new_plan(
            self,
            name: str,
            desc: str,
    ) -> str:
        pass

    @abstractmethod
    def update_plan(
            self,
    ):
        pass
