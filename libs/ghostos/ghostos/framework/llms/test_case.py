import threading
import time
import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from ghostos.core.llms import LLMs, Prompt, ModelConf, ServiceConf
from ghostos.core.messages import Message, MessageType


# 测试用, 不直接对外开放.

class APIInfo(BaseModel):
    api: str = Field(default="")
    service: Optional[ServiceConf] = Field(default=None)
    model: Optional[ModelConf] = Field(default=None)


class ChatCompletionTestResult(BaseModel):
    time: str = Field(default_factory=lambda: datetime.datetime.now().isoformat())
    results: Dict[str, Message] = Field(default_factory=dict)


class ChatCompletionTestCase(BaseModel):
    chat: Prompt
    apis: List[APIInfo]
    results: List[ChatCompletionTestResult] = Field(default_factory=list)


def run_test_cases(cases: ChatCompletionTestCase, llms: LLMs) -> Dict[str, Message]:
    result = {}
    threads = []
    for api_info in cases.apis:
        thread = threading.Thread(target=run_test_case, args=(api_info, cases.chat, llms, result))
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    # 先简单实现一下.
    return result


def run_test_case(api_info: APIInfo, chat: Prompt, llms: LLMs, result: Dict[str, Message]) -> None:
    api = None
    if api_info.api:
        api = llms.get_api(api_info.api)
    elif api_info.model:
        model = api_info.model
        service = api_info.service
        if service is None:
            service = llms.get_service(model.service)
        if service and model:
            api = llms.new_api(service, model)
    if api is None:
        raise ValueError(f'No API found for {api_info}')

    name = api.get_service().name + "." + api.get_model().model
    start = time.time()
    try:
        message = api.chat_completion(chat)
    except Exception as e:
        message = MessageType.ERROR.new(content=str(e))
    finally:
        end = time.time()
        duration = end - start
        print("+++ {case} is done in {duration:.2f} seconds +++".format(case=name, duration=duration))
    result[name] = message
