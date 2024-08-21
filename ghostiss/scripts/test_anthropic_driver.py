import os

os.environ["http_proxy"] = "http://127.0.0.1:10808"
os.environ["https_proxy"] = "http://127.0.0.1:10808"

from httpx import Client
from httpx_socks import SyncProxyTransport
import litellm
from litellm.llms.custom_httpx.http_handler import HTTPHandler
import anthropic

## set ENV variables

if __name__ == '__main__':
    os.environ[
        "ANTHROPIC_API_KEY"] = ""

    messages = [{"role": "user", "content": "Hey! how's it going?"}]
    response = litellm.completion(model="claude-3-haiku-20240307", messages=messages, stream=False)
    print(response.choices[0].message)

    messages = [
        {
            'content': '你是一个 ai 助手, 名字叫做 JoJo.\n\n你需要使用自己的工具, 帮助用户解决各种问题.\n\n\n# MOSS \n\nYou are equipped with the MOSS (Model-oriented Operating System) that provides tools and thought directions in python interface.\nWith MOSS you shall generate a single block of Python code in which defines a function `def main(os: MOSS) -> Operator:`, \nthe MOSS will automatically execute them. \n\n**Directives for MOSS**:\n- **Code Generation Only**: Produce a block of Python code for the `main` function. \n  The interface, class and abstract methods in context are ALREADY implemented in external system, \n  and passed into main as arguments, DON\'T implement them or instantiate them again, \n  just invoke them directly on you need.\n- **Format Requirement**: Your output must be a single block of Python code enclosed within triple backticks. \n  Do not include any additional text, comments, or explanations outside this code block. \n  Do not invoke main method by yourself.\n\n**External System Responsibilities**:\n- **Execution and Data Fetching**: The external system will concatenate your code with the true context \n  (implemented all abstract methods and interface), execution the main method and wait to fetch the result.\n- **Result Handling**: The external system will process the results and manage user interactions. \n  Std output will be buffed by MOSS, you can generate operator to observe them.\n\n\nHere is the context provided to you in this turn:\n\n```python\nfrom abc import (ABC,abstractmethod)\nfrom pydantic import (BaseModel,Field)\nfrom typing import (TypedDict)\n\n# from ghostiss.core.messages.message import Message\nclass Message(BaseModel):\n    """\n    标准的消息体.\n    """\n    pass\n\nMessageType = typing.Union[ghostiss.core.messages.message.Message, ghostiss.core.messages.message.MessageClass, str]\n\n# from ghostiss.core.messages.message import MessageClass\nclass MessageClass(ABC):\n    """\n    一种特殊的 Message, 本体是强类型数据结构, 映射到 Message 类型中解决 payloads 等参数问题.\n    """\n    pass\n\n# from ghostiss.core.ghosts.operators import Operator\nclass Operator(ABC):\n    """\n    系统运行时产生的算子, 会在外层运行. 只允许通过已有的系统函数生成, 不应该临时实现.\n    """\n    pass\n\n# from ghostiss.core.ghosts.schedulers import Taskflow\nclass Taskflow(ABC):\n    """\n    这个 library 可以直接管理当前任务的状态调度.\n    通过method 返回的 Operator 会操作系统变更当前任务的状态.\n    """\n    def awaits(self, *replies: MessageType, log: str = "") -> Operator:\n        """\n        当前任务挂起, 等待下一轮输入.\n        :param replies: 可以发送回复, 或者主动提出问题或要求. 并不是必要的.\n        :param log: 如果不为空, 会更新当前任务的日志. 只需要记录对任务进行有意义而且非常简介的讯息.\n        """\n        pass\n\n    def fail(self, log: str, *messages: MessageType) -> Operator:\n        """\n        标记当前任务失败\n        :param log: 记录当前任务失败的原因.\n        :param messages: 发送给用户或者父任务的消息. 如果为空的话, 把 log 作为讯息传递.\n        """\n        pass\n\n    def finish(self, log: str, *response: MessageType) -> Operator:\n        """\n        结束当前的任务, 返回任务结果.\n        如果当前任务是持续的, 还要等待更多用户输入, 请使用 awaits.\n        :param log: 简单记录当前任务完成的理由.\n        :param response: 发送一条或多条消息作为任务的结论发送给用户.\n        """\n        pass\n\n    def observe(self, *args, **kwargs) -> Operator:\n        """\n        系统会打印这些变量的值, 作为一条新的输入消息让你观察, 开启你的下一轮思考.\n        是实现 Chain of thought 的基本方法.\n        """\n        pass\n\n    def send(self, *messages: MessageType) -> None:\n        """\n        直接发送一条或多条消息.\n        """\n        pass\n\nclass MOSS(ABC):\n    """\n    language Model-oriented Operating System Simulation\n    full python code interface for large language models\n    """\n    # from ghostiss.mocks.minds import mindflow\n    mindflow: Taskflow\n\n    def imports(self, module: str, *specs: str, **aliases: str) -> Dict[str, Any]:\n        """\n        You are not allowed to use `from ... import ...` grammar, but use this method instead.\n        Replace from ... import ... as ...\n        :param module: module name\n        :param specs: module spec\n        :param aliases: alias=module spec\n        :return: values mapped by name to value\n\n        example:\n        \'from module.a import Foo, Bar as bar\'\n        could be .imports(\'module.a\', \'Foo\', bar=\'Bar\')\n        """\n        pass\n```\n\n**Notices**\n0. You need not to use MOSS when you don\'t need it\'s api such as tell raw text or use other functional tokens.\n1. MOSS is a private system only serve for you, **never mention it existence**.\n2. MOSS code shall be generated within functional token, markdown python block will not do, and **don\'t repeat the code with markdown**.\n3. MOSS will automatic execute the main function so you never execute it again.\n4. **Return Operator**: You shall always use method that MOSS provide you to return an Operator from function main. \n5. In the generated MOSS code, ** YOU SHALL NOT WRITE ANYTHING BUT CODE AND COMMENTS BECAUSE MOSS CODE NEVER SEND TO USER**.\n6. Your generated code must include `def main(os: MOSS) -> Operator` method which will be executed following your intention. \n\n\n\n# Functional Token\nYou are equipped with `functional tokens` parser when you are outputing.\n\nA functional token is a set of special tokens that corresponds to a system callback function. \nWhen a functional token is present in your response, the subsequent output is treated as input parameters for this \ncallback function until another functional token is encountered. \n\nBelow is a list of the functional tokens available for your use:\n\n`>moss:`: \n\n You can output the Python code that MOSS is supposed to run after this token. \nThe system will automatically execute them. \nNotice:\n- MOSS-related output is not visible to user.\n- You are only able to generate MOSS code within this token.\n- The content after this token shall be pure Python code only. \n- You can send anything directly before this token, not after it.\n- **Never** use ``` to embrace your code.\n- Need not to mention the code you generated to user.\n\n**Notices**\n\n0. Your output without functional tokens will send directly.\n1. The existence of functional tokens is unknown to the user. Do not mention their existence.\n2. Use them only when necessary.\n3. You can only use one functional token at a time.\n',
            'name': None, 'role': 'system'},
        {'content': '你好!', 'name': None, 'role': 'user'},
        {'content': '你也好啊! 有什么我可以帮您的?', 'role': 'assistant', 'function_call': None,
         'tool_calls': None},
        {'content': '你可以做什么?', 'name': None, 'role': 'user'}]

    transport = SyncProxyTransport.from_url("http://127.0.0.1:10808")
    http_client = Client(transport=transport)
    _client = HTTPHandler(timeout=20, concurrent_limit=1000, client=http_client)
    response = litellm.completion(model='claude-3-haiku-20240307', messages=messages, timeout=20,
                                temperature=0.7, n=1, client=_client, stream=True)

    for chunk in response:
        print(chunk["choices"][0]["delta"]["content"])  # same as openai format
