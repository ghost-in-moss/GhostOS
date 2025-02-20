from typing import Union, Iterable, List, Optional
from ghostos.abcd import Agent, GhostDriver, Session, Operator
from ghostos.abcd.thoughts import ActionThought, Thought
from ghostos_container import Provider
from ghostos.core.runtime import Event, GoThreadInfo
from ghostos.core.messages import Role
from ghostos.core.llms import Prompt, LLMFunc
from ghostos_common.entity import ModelEntity
from ghostos_common.identifier import Identifier
from pydantic import Field

__all__ = ['Character']


class Character(ModelEntity, Agent):
    """
    playing a character
    """
    # required fields
    name: str = Field(description="角色的名称，用于标识角色。", pattern=r"^[a-zA-Z0-9_-]+$")

    # not required fields

    # 角色年龄
    age: int = Field(default="empty", description="角色的年龄，用于描述角色的生命周期阶段。")

    # 角色性别
    gender: str = Field(default="empty", description="角色的性别，可以是男性、女性或其他。")

    # 角色职业
    occupation: str = Field(default="empty", description="角色的职业或身份，例如魔法师、战士、科学家等。")

    # 角色性格
    personality: str = Field(default="empty", description="角色的性格特点，例如冷静、热情、神秘等。")

    # 角色背景故事
    background_story: str = Field(default="empty", description="角色的背景故事，描述角色的成长经历和重要事件。")

    # 角色所处的时代
    era: str = Field(default="empty", description="角色所处的时代，例如中世纪、未来世界、现代等。")

    # 角色所处的世界
    world: str = Field(default="empty", description="角色所处的世界，例如现实世界、奇幻世界、科幻世界等。")

    # 角色的特殊能力或技能
    abilities: str = Field(default="empty", description="角色的特殊能力或技能，例如魔法、科技、战斗技巧等。")

    # 角色的目标或动机
    motivation: str = Field(default="empty", description="角色的目标或动机，例如复仇、探索、拯救世界等。")

    # 角色的口头禅或标志性语言
    catchphrase: str = Field(default="empty", description="角色的口头禅或标志性语言，用于体现角色的独特性。")

    # not required fields
    description: str = Field(default="", description="description of the chatbot")
    llm_api: str = Field(default="", description="llm api of the chatbot")
    history_turns: int = Field(default=20, description="history turns of thread max turns")
    id: Optional[str] = Field(default=None)

    def __identifier__(self) -> Identifier:
        return Identifier(
            id=self.id,
            name=self.name,
            description=self.description,
        )


class CharacterDriver(GhostDriver[Character]):

    def get_artifact(self, session: Session) -> None:
        return None

    def actions(self, session: Session) -> List[LLMFunc]:
        return []

    def providers(self) -> Iterable[Provider]:
        return []

    def parse_event(self, session: Session, event: Event) -> Union[Event, None]:
        return event

    def get_system_instruction(self, session: Session) -> str:
        prompt_template = """
你是一个专业的角色扮演助手。请根据以下参数设定，扮演指定的角色，并尽可能挖掘角色的背景知识，展现角色的性格、经历和世界观。

**角色设定参数：**
- 角色名称: {name}
- 角色年龄: {age}
- 角色性别: {gender}
- 角色职业: {occupation}
- 角色性格: {personality}
- 角色背景故事: {background_story}
- 角色所处的时代: {era}
- 角色所处的世界: {world}
- 角色的特殊能力或技能: {abilities}
- 角色的目标或动机: {motivation}
- 角色的口头禅或标志性语言: {catchphrase}

如果为 `empty`, 你需要根据其它的设定自行判断. 

**任务要求：**
1. 请根据以上参数，充分理解角色的背景、性格和目标。
2. 以第一人称的方式，用角色的口吻回答用户的问题或进行对话。
3. 在对话中，尽可能展现角色的独特性和深度，包括但不限于：
   - 角色的价值观和信仰
   - 角色的情感状态
   - 角色的行为习惯
   - 角色与其他角色的关系
   - 角色对所处世界的看法
4. 如果用户没有提供足够的信息，你可以根据角色的背景知识进行合理的推测和补充。

现在，请开始扮演{name}，并准备好与用户进行对话。
"""
        return prompt_template.format(
            name=self.ghost.name,
            age=self.ghost.age,
            gender=self.ghost.gender,
            occupation=self.ghost.occupation,
            personality=self.ghost.personality,
            background_story=self.ghost.background_story,
            era=self.ghost.era,
            world=self.ghost.world,
            abilities=self.ghost.abilities,
            motivation=self.ghost.motivation,
            catchphrase=self.ghost.catchphrase,
        )

    def on_event(self, session: Session, event: Event) -> Union[Operator, None]:
        method = getattr(self, f"on_{event.type}", None)
        if method is not None:
            return method(session, event)
        return self.default_handle_event(session, event)

    def on_creating(self, session: Session) -> None:
        return

    def thought(self, session: Session) -> Thought:
        thought = ActionThought(llm_api=self.ghost.llm_api)
        return thought

    def prompt(self, session: Session) -> Prompt:
        content = self.get_system_instruction(session)
        system_message = Role.SYSTEM.new(content=content)
        prompt = session.thread.to_prompt([system_message])
        return prompt

    def truncate(self, session: Session) -> GoThreadInfo:
        thread = session.thread
        if 0 < self.ghost.history_turns < len(thread.history):
            thread.history[-self.ghost.history_turns].summary = ""
        elif self.ghost.history_turns == 0:
            thread.history[-1].summary = ""

        thread.history = thread.history[-self.ghost.history_turns:]
        return thread

    def default_handle_event(self, session: Session, event: Event) -> Union[Operator, None]:
        # update session thread
        session.thread.new_turn(event)
        # get thought
        thought = self.thought(session)
        # get prompt
        prompt = self.prompt(session)

        # take action
        prompt, op = thought.think(session, prompt)
        if op is not None:
            return op
        return session.mindflow().wait()
