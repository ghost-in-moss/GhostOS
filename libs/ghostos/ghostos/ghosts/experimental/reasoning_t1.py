from typing import List

from ghostos.abcd import Session, Thought, ActionThought, ChainOfThoughts
from ghostos.ghosts.chatbot import Chatbot, ChatbotDriver
from ghostos.thoughts.meta_prompt_experiments import MetaPromptExp1
from pydantic import BaseModel, Field


class ReasoningChatbotT1(Chatbot):
    reasoning: List[str] = Field(
        default_factory=lambda: [
            "第一步, 你先要结合上下文, 理解清楚用户的意图, 补全它字面上缺失的上下文讯息, 你的补完如下:",
            "第二步, 你需要根据用户意图, 以及你得到的指令, 将值得关注的指令整理一遍, 你的整理结果如下:",
            "第三步, 你需要根据用户意图, 你整理的指令, 结合你拥有的知识, 把你应答的思路先提纲挈领地写出来, 你的思路如下:",
            # 再思可也.
            "第四步, 你需要反思你对用户意图的理解, 对指令的要点整理, 你的应答思路, 看看有没有要修改的细节. 如果有需要修改的请写出来, 否则回复 done. 你的回复:",
        ]
    )


class ReasoningChatbotT1Driver(ChatbotDriver):

    def __init__(self, ghost: ReasoningChatbotT1):
        super().__init__(ghost)

    def thought(self, session: Session) -> Thought:
        return ChainOfThoughts(
            final=ActionThought(
                llm_api=self.ghost.llm_api,
                actions=self.actions(session),
            ),
            chain=[
                MetaPromptExp1(
                    llm_api_name=self.ghost.llm_api,
                    reasoning=self.ghost.reasoning,
                ),
            ]
        )
