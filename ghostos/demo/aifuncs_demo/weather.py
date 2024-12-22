from typing import Optional
from ghostos.core.aifunc import AIFunc, AIFuncResult
from pydantic import Field


class WeatherAIFunc(AIFunc):
    """
    tell about weather
    """
    city: str = Field(default="", description="the city name that you want weather forecast. empty means local")
    date: str = Field(default="today", description="the date of weather forecast")


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


# <moss-hide>

def __aifunc_instruction__(fn: WeatherAIFunc) -> str:
    return "Your task is using get_weather function to get weather information fit the input"




example = WeatherAIFunc()
# </moss-hide>
