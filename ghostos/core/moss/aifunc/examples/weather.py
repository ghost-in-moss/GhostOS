from typing import Optional
from ghostos.core.moss.aifunc import AIFunc, AIFuncResult
from ghostos.core.moss.aifunc.examples.utils import get_weather
from ghostos.core.moss import Moss
from pydantic import Field


class WeatherAIFuncResult(AIFuncResult):
    """
    weather result
    """
    result: str = Field(description="the full result describing weather details in nature language form.")
    date: str = Field(default="today", description="the date of weather forecast")
    city: str = Field(default="", description="the city name that you want weather forecast. empty means local")
    temperature: Optional[float] = Field(default=None, description="the temperature of the weather")
    humidity: Optional[float] = Field(default=None, description="the humidity of the weather")
    pressure: Optional[float] = Field(default=None, description="the pressure of the weather")
    wind_speed: Optional[float] = Field(default=None, description="the wind speed of the weather")
    wind_dir: Optional[float] = Field(default=None, description="the wind direction of the weather")


# <moss>


class WeatherAIFunc(AIFunc):
    """
    tell about weather
    """
    request: str = Field(description="user's request about the weather.")


def __aifunc_instruction__(fn: WeatherAIFunc) -> str:
    return (
        f"your request is: {fn.request}."
    )


example = WeatherAIFunc(request="北京明天究竟是什么天气哈？")
# </moss>
