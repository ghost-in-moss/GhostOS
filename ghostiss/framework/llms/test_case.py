import threading
import time
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from ghostiss.core.runtime.llms import LLMs, Chat, ModelConf, ServiceConf
from ghostiss.core.messages import Message, DefaultTypes


# 测试用, 不直接对外开放.

class APIInfo(BaseModel):
    api: str = Field(default="")
    service: Optional[ServiceConf] = Field(default=None)
    model: Optional[ModelConf] = Field(default=None)


class ChatCompletionTestCase(BaseModel):
    chat: Chat
    apis: List[APIInfo]


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


def run_test_case(api_info: APIInfo, chat: Chat, llms: LLMs, result: Dict[str, Message]) -> None:
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
        message = DefaultTypes.ERROR.new(content=str(e))
    finally:
        end = time.time()
        duration = end - start
        print("+++ {case} is done in {duration:.2f} seconds +++".format(case=name, duration=duration))
    result[name] = message
