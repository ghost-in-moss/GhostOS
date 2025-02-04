from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional
from typing_extensions import Self
from pydantic import BaseModel, Field
from ghostos.core.messages import Message
from ghostos.core.llms import LLMApi, LLMs, Prompt, ModelConf
from ghostos.bootstrap import get_container

"""
模型的高级封装可以有很多种机制, 层层封装的目的是化繁为简. 有很多种方案: 
1. Agent: 模型封装到一个可以多轮对话的实体中. 
2. AIFunc: 模型被封装到一个函数里, 可以根据入参独立做多轮思考, 直到写出可运行的代码并执行.
3. ModelFunc: 模型被封装到一个函数, 不进行多轮思考, 而是直接根据入参给出结果. 

这个文件实现的是 ModelFunc. 它本身可以由模型生成. 
"""

R = TypeVar("R")


class ModelFunc(Generic[R], ABC):
    """
    model func is a simple function wrapper of models.
    1. the model func self is a pydantic model, so the instance of it is the same as arguments of a function.
    2. the model func shall parse arguments into the model arguments.
    3. the model func call a certain model with the model arguments.
    4. the model func parse the result from the model, and convert it into the model function result R.
    """

    @abstractmethod
    def run(self) -> R:
        """
        generate the model func result.
        """
        # 1. parse self attributes into the model arguments.
        # 2. call the model with the model arguments.
        # 3. get the result, and parse the result to the ModelFunc result type R.
        # 4. handle the exceptions (optional)
        pass


class LLMModelFunc(BaseModel, ModelFunc[R], ABC):
    """
    LLM model func is a simple ModelFunc driven by LLM.
    """
    llm_api: str = Field(
        default="",
        description="the llm api name, empty means default. the option is available to all the llm model func.",
    )
    model: Optional[ModelConf] = Field(
        default=None,
        description="the model conf instead of the llm api name",
    )

    def with_model(self, model: ModelConf) -> Self:
        self.model = model
        return self

    @abstractmethod
    def run(self) -> R:
        # 1. parse the self attributes into openai model message params (dict)
        # 2. call _generate method, get the string result from the model.
        # 3. parse the result from the model output.
        pass

    def _generate(self, messages: list[dict]) -> str:
        """
        :param messages: openai message type in dict. {"role": str, "content": str}
        :return: model generation.
        """
        parsed = []
        for item in messages:
            msg = Message(**item)
            msg = msg.as_tail(copy=False)
            parsed.append(msg)
        prompt = Prompt.new_from_messages(parsed)
        return self._generate_from_prompt(prompt)

    def _generate_from_prompt(self, prompt: Prompt) -> str:
        llm_api = self._get_llm_api()
        done = llm_api.chat_completion(prompt)
        return done.get_content()

    def _get_llm_api(self) -> LLMApi:
        container = get_container()
        llms = container.get(LLMs)
        if self.model is not None:
            return llms.new_model_api(self.model)

        return llms.get_api(self.llm_api)
