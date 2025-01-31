from typing import Tuple, Optional, List

from ghostos.abcd import Session, Operator
from ghostos.abcd.thoughts import Thought, T
from ghostos.core.llms import Prompt, LLMs
from ghostos.core.messages import Role, MessageStage
from pydantic import BaseModel, Field


class MetaPromptExp1(BaseModel, Thought[Operator]):
    """
    实现一个用来做基线测试, 只能进行线性思考的 Reasoning Thought.
    """

    llm_api_name: str = Field(default="", description="Name of the LLM API")
    inform: str = Field(default="""
你现在进入了思考模式, 在思考模式中, 你在自己和自己说话. 所以你应该用 "我" 来讨论自己应该干什么. 
在思考模式中, 你所有的输出不会发送给用户, 而是作为你脑海中的想象供你未来使用.
你需要通过这些想象让你最终的决策更加正确. 
解下来系统指令会引导你一步步思考. 
""")
    reasoning: List[str] = Field(description="the instruction node of the reasoning")

    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[Operator]]:
        if len(self.reasoning) == 0:
            return prompt, None

        llm_api = session.container.force_fetch(LLMs).get_api(self.llm_api_name)
        _prompt = prompt.model_copy(deep=True)
        _reasoning = []
        _prompt.added.append(Role.new_system(self.inform))
        for node in self.reasoning:
            instruction = Role.new_system(content=node)
            instruction.stage = MessageStage.REASONING.value
            _prompt.added.append(instruction)

            # messenger = session.messenger(stage=MessageStage.REASONING.value)
            # messenger.send([instruction])
            # messenger.flush()

            messenger = session.messenger(stage=MessageStage.REASONING.value)
            items = llm_api.deliver_chat_completion(_prompt, not messenger.completes_only())
            messenger.send(items)
            messages, _ = messenger.flush()
            _prompt.added.extend(messages)
            _reasoning.extend(messages)

        prompt.added.extend(_reasoning)
        return prompt, None


class MetaPromptExp2(BaseModel, Thought[Operator]):
    """
    实验2, 只思考一步.
    """
    llm_api_name: str = Field(default="", description="Name of the LLM API")
    instruction: str = Field(default="""
你现在进入了思考模式, 在思考模式中, 你在自己和自己说话. 所以你应该用 "我" 来讨论自己应该干什么. 
在思考模式中, 你所有的输出不会发送给用户, 而是作为你脑海中的想象供你未来使用.
你需要先回答以下几个问题: 
1. 用户的意图是什么, 更完整的表达内容应该是什么.
2. 结合上下文与用户的意图, 回顾你得到的所有指令, 你应该注意哪些事项.
3. 根据以上思考, 你需要将你的思路写成给自己的 Chain of thoughts.
现在请给出你写的 Chain of thoughts:
""")

    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[T]]:
        _prompt = prompt.model_copy(deep=True)
        _reasoning = []
        instruction = Role.new_system(content=self.instruction)
        instruction.stage = MessageStage.REASONING.value
        _prompt.added.append(instruction)

        # messenger = session.messenger(stage=MessageStage.REASONING.value)
        # messenger.send([instruction])
        # messenger.flush()

        messenger = session.messenger(stage=MessageStage.REASONING.value)
        llm_api = session.container.force_fetch(LLMs).get_api(self.llm_api_name)
        items = llm_api.deliver_chat_completion(_prompt, not messenger.completes_only())
        messenger.send(items)
        messages, _ = messenger.flush()
        _prompt.added.extend(messages)
        _reasoning.extend(messages)
        prompt.added.extend(_reasoning)
        return prompt, None


class MetaPromptExp3(BaseModel, Thought[Operator]):
    """
    实验3, 一步一步思考.
    """
    llm_api_name: str = Field(default="", description="Name of the LLM API")
    max_think_steps: int = Field(default=50, description="the maximum number of think steps")
    start_instruction: str = Field(default="""
你现在进入了思考模式, 在思考模式中, 你在自己和自己说话. 所以你应该用 "我" 来讨论自己应该干什么. 
在思考模式中, 你所有的输出不会发送给用户, 而是作为你脑海中的想象供你未来使用.
你接下来的思考应该使用这种方式: 
1. 观察之前的思考内容, 反思是不是有问题, 或者突然有新的灵感. 如果上一步没有完成的话, 你仍然应该继续上一步的思考. 
2. 确定一次只思考一步, 想清楚你现在这一步应该干什么, 并把要做的事情写出来. 
3. 按你思考的这一步, 尝试做一轮推演. 只做一轮推演, 等待下一轮观察反思上一轮思考结果. 
4. 如果你非常确信, 每一步思考都完成了, 你应该把 `[done]` 作为你输出的结尾. 这样思维链就会中断, 进入回复模式. 
5. 如果你的计划没有执行完, 你不应该认为思考结束了. 
6. 不需要一次思考完, 你想得太多了后, 可以先输出一部分, 然后等待. 系统会自动调度你下一次观察和反思.

接下来开始你的思考: 
""")
    step_instruction: str = Field(
        default="""
以上是你之前的思考过程. 你现在要: 
1. 观察之前的思考内容, 反思是不是有问题, 或者突然有新的灵感. 如果上一步没有完成的话, 你仍然应该继续上一步的思考. 
2. 确定一次只思考一步, 想清楚你现在这一步应该干什么, 并把要做的事情写出来. 
3. 按你思考的这一步, 尝试做一轮推演. 只做一轮推演, 等待下一轮观察反思上一轮思考结果. 
4. 如果你非常确信, 每一步思考都完成了, 你应该把 `[done]` 作为你输出的结尾. 这样思维链就会中断, 进入回复模式. 
5. 如果你的思考空间不够, 请用 `[continue]` 作为输出的结尾, 这样系统会自动调度你下一次的观察和反思. 

请输出你的思考: 
"""
    )

    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[T]]:
        _reasoning = []
        instruction = Role.new_system(content=self.start_instruction)
        instruction.stage = MessageStage.REASONING.value

        # messenger = session.messenger(stage=MessageStage.REASONING.value)
        # messenger.send([instruction])
        # messenger.flush()
        llm_api = session.container.force_fetch(LLMs).get_api(self.llm_api_name)
        count = 0
        while count < self.max_think_steps:
            _prompt = prompt.model_copy(deep=True)
            _prompt.added.append(instruction)
            _prompt.added.extend(_reasoning)

            if count > 0:
                _prompt.added.append(
                    Role.new_system(
                        content=self.step_instruction,
                        stage=MessageStage.REASONING.value,
                    )
                )

            messenger = session.messenger(stage=MessageStage.REASONING.value)
            items = llm_api.deliver_chat_completion(_prompt, not messenger.completes_only())
            messenger.send(items)
            messages, _ = messenger.flush()
            _reasoning.extend(messages)
            if messages[-1].get_content().endswith("[done]"):
                break
            count += 1

        prompt.added.extend(_reasoning)
        session.thread.append(*_reasoning)
        prompt.added.append(
            Role.new_system(
                content="以上是你的思考过程, 接下来请根据思考成果, 围绕用户要求作出回答. 注意不要对用户复述你的思维过程.",
            )
        )
        return prompt, None
