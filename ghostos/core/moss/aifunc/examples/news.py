from typing import Optional, List
from ghostos.core.moss.aifunc import AIFunc, AIFuncResult
from pydantic import BaseModel, Field
from ghostos.core.moss import Moss


class NewsAIFuncResult(AIFuncResult):
    """
    news result
    """

    class News(BaseModel):
        summary: str = Field(description="summary of the news.")
        title: str = Field(description="title of the news.")
        date: str = Field(description="date of the news.")
        media: str = Field(description="media of the news.")

    results: List[News] = Field(default_factory=list)


__result_type__ = NewsAIFuncResult


# <moss>

class NewsAIFunc(AIFunc):
    """
    search news
    """
    request: str = Field(description="user's request about the news he want.")
    limit: int = Field(default=5, description="how many news you want.")


def __aifunc_instruction__(fn: NewsAIFunc) -> str:
    return (
        "Your task is **MOCK** a fake result from the function arguments, make it seems real."
        f"your request is: {fn.request}, limit is {fn.limit}"
    )


example = NewsAIFunc(request="我想知道黑神话悟空这款游戏的媒体评分。")

# </moss>
