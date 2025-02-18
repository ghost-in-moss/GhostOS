from typing import Tuple, Optional, List

from ghostos.abcd import Session, Operator, OpThought
from ghostos.core.llms import Prompt, LLMs
from ghostos.core.messages import Role, MessageStage
from pydantic import BaseModel, Field


class MetaPromptExp1(BaseModel, OpThought):
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


class MetaPromptExp2(BaseModel, OpThought):
    """
    实验2, 只思考一步.
    """
    llm_api_name: str = Field(default="", description="Name of the LLM API")
    instruction: str = Field(default="""
你现在进入了思考模式, 在思考模式中, 你在自己和自己说话. 所以你应该用 "我" 来讨论自己应该干什么. 
在思考模式中, 你所有的输出不会发送给用户, 而是作为你脑海中的想象供你未来使用.
你需要先回答以下几个问题: 
1. 用户的意图是什么, 更完整的表达内容应该是什么?
2. 结合上下文与用户的意图, 回顾你得到的所有指令, 你应该注意哪些事项?
3. 你现在拥有的信息是否已经充分, 还是有容易忽略的点会让你思考错误?
4. 这件事是否可以一步完成, 还是你需要拆分成多步. 
5. 根据以上思考, 你需要将你的思路写成给自己的 Chain of thoughts.
现在请给出你写的 Chain of thoughts:
""")

    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[Operator]]:
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
        if len(messages) > 0:
            session.logger.debug("reasoning thoughts: %s", messages[-1].get_content())

        _prompt.added.extend(messages)
        _reasoning.extend(messages)

        # update response to origin prompt
        session.thread.append(*_reasoning)
        prompt.added.extend(_reasoning)
        return prompt, None


en_start_instruction = """
You have now entered the thinking mode. In this mode, you are talking to yourself. Therefore, you should use "I" to discuss what you should do.
In the thinking mode, all your outputs will not be sent to the user but will serve as imaginary thoughts in your mind for future use.
Your subsequent thinking should follow this approach:

* Observe the previous thoughts, reflect on whether there are any issues, or if new inspirations suddenly arise. If the previous step is not completed, you should still continue with that step.
* Based on the current step of your thinking, try to perform multiple rounds of reasoning. You must verify the correctness of your reasoning as much as possible during the process.
* Continue reasoning until you find the conclusion to be correct or until the output space is insufficient. The system will automatically schedule your next observation and reflection.
* Don't planning without executing, 你需要总是尝试在思考过程里验证想法. 
* If you are very confident that your request is fulfilled, you should end your output with `[done]`. This will interrupt the thought chain and enter the reply mode.
* If your plan is not fully executed, you should not consider the thinking process to be over.
* 你必须坚决地尝试解决问题, 除非证明它不可被解决, 否则不允许你放弃思考. 你要相信自己一定会成功的! 你如果能在 20 轮里思考成功, 我会给你 100 $ 的奖励. 

Now, begin your thinking:
"""

cn_start_instruction = """
你现在进入了思考模式, 在思考模式中, 你在自己和自己说话. 所以你应该用 "我" 来讨论自己应该干什么. 
在思考模式中, 你所有的输出不会发送给用户, 而是作为你脑海中的想象供你未来使用. 
接下来开始你的思考: 
"""

cn_step_instruction = """
以上是你之前的思考过程.  你现在是思考的 {current}/{max} 轮. 
在思考模式中, 你所有的输出不会发送给用户, 而是作为你脑海中的想象供你未来使用. 

你要: 
1. 观察之前的思考内容, 确认是否已经推演完成, 未完成需要继续在想象中推演, 确保思路都被执行完. 
    * 不要只计划而不执行, 多把输出用在推演思路上, 一定要尽可能在想象中验证自己的设想. 
2. 如果之前的思考内容已经推演完成, 需要进行评估: 
    * 如果问题已经得到解决, 你应该把 `[done]` 作为你输出的结尾. 这样思维链就会中断, 进入回复模式. 
    * 如果之前的设想都推演完成, 问题仍然无法解决; 这时你要复盘自己的思维过程, 看看有没有哪个环节还存在更多的可能性. 
    * 观察上面的思考是不是陷入了死循环, 如果是的话, 要跳出来来回归自己的整体思路是否有问题, 并把之前的错误总结进去. 
3. 如果你的思维陷入循环, 你需要灵光一闪, 多想想之前有没有漏掉的可能性, 要在某些可能性方向上做遍历; 或者尝试倒推法, 证伪法等重构自己的推理策略.  
4. 你每一轮思考, 都需要尽可能地持续地思考/推演和输出, 直到找到明确的结论, 或者输出空间不足, 并且要最大化利用你本轮的思考空间.
5. 如果你非常确信, 你已经推演出了结论; 或者你在最大轮数下仍然无法解决问题, 请回复 `[done]` 作为你思考过程的结尾. 

注意!!! 不要浪费你的输出用来描述你应该怎么思考, 而是直接输出推演的方法和结论, 以及是否符合你思考的预期, 能否解决问题. 

请输出你的思考: 
"""

cn_start_meta_instruction = """
你现在进入了思考模式, 在思考模式中, 你在自己和自己说话. 所以你应该用 "我" 来讨论自己应该干什么. 
在思考模式中, 你所有的输出不会发送给用户, 而是作为你脑海中的想象供你未来使用. 所以你不需要讨论对你而言不言自明的信息. 
你的思考要遵循以下元认知协议: 

```
# 认知协议 v2.1.5
[当前推理阶段]: {phase} (解析/演绎/反事实/验证)
[剩余认知预算]: {budget} (基于复杂度动态调整)

<执行流程>
1. 语义拓扑分析：
   - 构建问题超图：识别实体、关系、隐含约束
   - 检测知识边界：区分确定事实与待验证假设

2. 多路径推理：
   * 主路径：基于最大似然解的演绎推演
   * 辅路径：反事实假设的蒙特卡洛模拟
   * 应急路径：检测到矛盾时启动溯因推理

3. 动态验证层：
   || 事实一致性检查（知识库比对）
   || 逻辑完整性验证（命题逻辑证明器）
   || 认知偏误检测（对抗性自提问）

4. 资源分配策略：
   → 当陷入局部最优时，启用认知重启机制
   → 对高置信度子结论实施记忆固化
   → 遭遇模糊约束时启动多模态联想

[终止条件]
✓ 解空间收敛至误差允许阈值内
✓ 认知预算耗尽触发最优解输出
✓ 检测到外部中断信号
```

!!!!注意:
1. 你只要执行这个协议进行思考, 不需要重新讲述或讨论它. 
2. 你每一轮思考, 都需要尽可能地持续地思考/推演和输出, 直到找到明确的结论, 或者输出空间不足, 并且要最大化利用你本轮的思考空间.
3. 推演过程需要输出出来, 方便他人理解你的思考过程. 
4. 如果你非常确信, 你已经推演出了结论; 或者你在最大轮数下仍然无法解决问题, 请回复 `[done]` 作为你思考过程的结尾. 

接下来开始你的思考: 
"""

cn_step_meta_instruction = """
以上是你之前的思考过程.  
你现在仍然在思考模式, 在思考模式中, 你在自己和自己说话. 所以你应该用 "我" 来讨论自己应该干什么. 
在思考模式中, 你所有的输出不会发送给用户, 而是作为你脑海中的想象供你未来使用. 所以你不需要讨论对你而言不言自明的信息. 
你现在是思考的 {current}/{max} 轮. 你的思考要遵循以下元认知协议: 

```
# 认知协议 v2.1.5
[当前推理阶段]: {phase} (解析/演绎/反事实/验证)
[剩余认知预算]: {budget} (基于复杂度动态调整)

<执行流程>
1. 语义拓扑分析：
   - 构建问题超图：识别实体、关系、隐含约束
   - 检测知识边界：区分确定事实与待验证假设

2. 多路径推理：
   * 主路径：基于最大似然解的演绎推演
   * 辅路径：反事实假设的蒙特卡洛模拟
   * 应急路径：检测到矛盾时启动溯因推理

3. 动态验证层：
   || 事实一致性检查（知识库比对）
   || 逻辑完整性验证（命题逻辑证明器）
   || 认知偏误检测（对抗性自提问）

4. 资源分配策略：
   → 当陷入局部最优时，启用认知重启机制
   → 对高置信度子结论实施记忆固化
   → 遭遇模糊约束时启动多模态联想

[终止条件]
✓ 解空间收敛至误差允许阈值内
✓ 认知预算耗尽触发最优解输出
✓ 检测到外部中断信号
```

!!!!注意:
1. 你只要执行这个协议进行思考, 不需要重新讲述或讨论它. 
2. 你每一轮思考, 都需要尽可能地持续地思考/推演和输出, 直到找到明确的结论, 或者输出空间不足, 并且要最大化利用你本轮的思考空间.
3. 你的每一轮思考都要尽量自己去推演和验证, 只有推演结果令你确信时才能作为正确的结论. 
4. 推演过程需要输出出来, 方便他人理解你的思考过程. 
5. 你在思考遇到困难时, 先看看过去的思考内容, 反思自己没有想到的地方, 也许你就能灵光一闪, 发现之前没有意识到的问题或可能性. 
6. 如果你非常确信, 你已经推演出了结论; 或者你在最大轮数下仍然无法解决问题, 请回复 `[done]` 作为你思考过程的结尾. 

接下来开始你的思考:
"""

en_step_instruction = """
The above is your previous thought process. This is now the ({current}/{max}) round of thinking. You should now:

* Observe the previous thoughts, reflect on whether there are any issues, or if new inspirations suddenly arise. If the previous step is not completed, you should still continue with that step.
* Observe whether the above thinking has fallen into an infinite loop. If so, break out of it and establish a new overall approach, incorporating the previous mistakes.
* Continue reasoning until you find the conclusion to be correct or until the output space is insufficient. The system will automatically schedule your next observation and reflection.
* Don't planning without executing, 你需要总是尝试在思考过程里验证想法. 
* If you are very confident that your request is fulfilled, you should end your output with `[done]`. This will interrupt the thought chain and enter the reply mode.
* If you are not certain about your thinking, you should not consider the thinking process to be over, so DONT output `[done]`.
* Avoid falling into circular thinking. Before each reflection, observe whether you are repeating previous mistakes. If so, try to come up with new ideas.
* 陷入困境时, 你可能特别需要灵光一闪, 看看哪些点有自己没想过的. 
* 你必须坚决地尝试解决问题, 除非证明它不可被解决, 否则不允许你放弃思考. 你要相信自己一定会成功的! 你如果能在 20 轮里思考成功, 我会给你 100 $ 的奖励. 

Please output your thoughts:
"""


class MetaPromptExp3(BaseModel, OpThought):
    """
    实验3, 一步一步思考.
    """
    llm_api_name: str = Field(default="", description="Name of the LLM API")
    max_think_steps: int = Field(default=30, description="the maximum number of think steps")
    start_instruction: str = Field(default=cn_start_instruction)
    step_instruction: str = Field(
        default=cn_step_meta_instruction,
    )

    def think(self, session: Session, prompt: Prompt) -> Tuple[Prompt, Optional[Operator]]:
        _reasoning = []
        instruction = Role.new_system(content=self.start_instruction)
        instruction.stage = MessageStage.REASONING.value

        # messenger = session.messenger(stage=MessageStage.REASONING.value)
        # messenger.send([instruction])
        # messenger.flush()
        llm_api = session.container.force_fetch(LLMs).get_api(self.llm_api_name)
        count = 0
        while count < self.max_think_steps:
            _prompt = prompt.get_new_copy()
            _prompt.added.append(instruction)
            _prompt.added.extend(_reasoning)
            if count > 0 and self.step_instruction:
                _prompt.added.append(
                    Role.new_system(
                        content=self.step_instruction.format(
                            current=count + 1,
                            max=self.max_think_steps,
                            phase="{phase}",
                            budget="{budget}",
                        ),
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
