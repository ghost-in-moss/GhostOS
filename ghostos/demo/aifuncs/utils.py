# fake methods for aifunc
from typing import Dict


def get_weather(city: str, date: str) -> Dict:
    """
    :param city: the city that you want
    :param date: the date you want
    :return: Dict that contains weather information:
        temperature: Optional[float]
        humidity: Optional[float]
        pressure: Optional[float]
        wind_speed: Optional[float]
        wind_dir: Optional[int] 0~360 degrees wind direction. 0 is North, 90 is East, etc.
    """
    return {
        "temperature": 30,
        "humidity": 80,
        "pressure": 100,
        "wind_speed": 6,
        "wind_dir": 95,
    }
