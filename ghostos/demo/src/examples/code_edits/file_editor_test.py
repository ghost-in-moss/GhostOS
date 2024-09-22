from typing import Optional
from pydantic import BaseModel, Field


class Caller(BaseModel):
    """
    消息协议中用来描述一个工具或者function 的调用请求.
    """
    id: Optional[str] = Field(default=None, description="caller 的 id, 用来 match openai 的 tool call 协议. ")
    name: str = Field(description="方法的名字.")
    arguments: str = Field(description="方法的参数. ")
    functional_token: bool = Field(default=False, description="caller 是否是基于协议生成的?")


if __name__ == '__main__':
    from ghostos.prototypes.console import quick_new_console_app
    from ghostos.thoughts import new_file_editor_thought
    app = quick_new_console_app(__file__, 4)
    app.run_thought(
        new_file_editor_thought(filepath=__file__),
        instruction="help me to replace all the chinese in this file into english please!"
    )
