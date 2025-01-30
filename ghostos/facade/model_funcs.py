from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from pydantic import BaseModel, Field
from ghostos.core.messages import Message
from ghostos.core.llms import LLMApi, LLMs, Prompt
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
        llm_api = self._get_llm_api()
        done = llm_api.chat_completion(prompt)
        return done.get_content()

    def _get_llm_api(self) -> LLMApi:
        container = get_container()
        llms = container.get(LLMs)
        return llms.get_api(self.llm_api)


class TextCompletion(LLMModelFunc[str]):
    """
    a very simple example of how to define a LLMModelFunc
    """

    text: str = Field(description="the text completion instruction.")

    def run(self) -> str:
        messages = [{"role": "user", "content": self.text}]
        return self._generate(messages)


class GenerateLLMModelFunc(LLMModelFunc[str]):

    quest: str = Field(description="")

    def run(self) -> str:
        with open(__file__, 'r') as f:
            source_code = f.read()

        # instruction is required to the model.
        instruction = f"""
Your request is to define a `LLMModelFunc` class that user want. 

The coding context about `LLMModelFunc` is:
```python
{source_code}
```
"""
        messages = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": self.quest},
        ]
        result = self._generate(messages)
        parts = result.rsplit("```python", 1)
        result = parts[0] if len(parts) == 1 else parts[1]
        return result.strip("```python").strip("```").strip()


if __name__ == "__main__":
    text = GenerateLLMModelFunc(
        quest="请帮我实现一个函数, 这个函数要, 从 N 个选项 (字符串) 中选择一个, 模型要输出选项的序号."
              "而这个函数把序号转换成选项的值, 返回出来."
    ).run()
    print(text)
