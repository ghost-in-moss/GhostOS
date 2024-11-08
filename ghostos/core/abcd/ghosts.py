from abc import ABC, abstractmethod
from ghostos.common import Identifier
from pydantic import BaseModel
from .concepts import Ghost, GhostDriver

"""
Some ghost prototypes. 
"""


class Agent(Ghost, ABC):
    """
    Agent is the base abstract of LLM-based conversational AI entity.

    The Model of the Agent defines its behavior, normally includes:
    - persona and instruction
    - configurations to create a context (cot/examples/knowledge/memory) for llm
    - llm configurations
    - tools
    - system configurations, like thread truncating / authorities / welcome craft etc.
    """

    Artifact = None

    @abstractmethod
    def __identifier__(self) -> Identifier:
        pass


class ChatBot(Agent, ABC):
    """
    Chatbot is the simplest kind of the Agents.
    Typical Chatbot is Customer Service or Internet search.
    Chat only means the most needed feature is to create a dialog-related but alternative context,
    for LLM in-context learning.
    """
    pass


class UserProxy(Ghost, ABC):
    """
    LLM-based UserProxy can understand human language and translate the user intends to system actions.
    It does not own any charactor or persona, is merely a Nature Language Interface of the system.
    Speed and Accuracy are the most important features.
    """
    pass


class Thought(BaseModel, Ghost, ABC):
    """
    Thought is a micro unit to processing thinking with current context;
    the Goal of the Thought is to produce a decision or suggestion, add them to the context.
    """
    Artifact = str

    @abstractmethod
    def __identifier__(self) -> Identifier:
        pass


class AIFunc(BaseModel, Ghost, ABC):
    """
    Act like a function but driven by AI models.
    AI models dynamic check the function call, and generate code in realtime.
    """

    @abstractmethod
    def __identifier__(self) -> Identifier:
        pass


class Workflow(Ghost, ABC):
    """
    workflow is a programmed Finite State Machine that does a certain job and return a certain result.
    The Goal of workflow is the result.
    Workflow itself is a FSM, but some node of it can be other ghost entity like AIFunc, Thought or Agent.
    """
    pass
