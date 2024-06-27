import threading
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from ghostiss.blueprint.kernel.llms import LLMs, Chat, ModelConf, ServiceConf
from ghostiss.blueprint.messages import Message, DefaultTypes


# 测试用, 不直接对外开放.

class APIInfo(BaseModel):
    api: str = Field(default="")
    service: Optional[ServiceConf] = Field(default=None)
    model: Optional[ModelConf] = Field(default=None)


class ChatCompletionTestCase(BaseModel):
    chat: Chat
    apis: Dict[str, APIInfo]


def run_test_cases(cases: ChatCompletionTestCase, llms: LLMs) -> Dict[str, Message]:
    result = {}
    threads = []
    for name, api_info in cases.apis.items():
        thread = threading.Thread(target=run_test_case, args=(name, api_info, cases.chat, llms, result))
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()
    return result


def run_test_case(name: str, api_info: APIInfo, chat: Chat, llms: LLMs, result: Dict[str, Message]) -> None:
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
        return

    try:
        message = api.chat_completion(chat)
    except Exception as e:
        message = DefaultTypes.ERROR.new(content=str(e))

    result[name] = message
