import sys
import argparse
import os
import yaml
from abc import ABC, abstractmethod
import datetime
from typing import Callable, List
from ghostiss.container import Container
from ghostiss.core.runtime.llms import LLMs
from ghostiss.core.moss.moss import MOSS, BasicMOSSImpl, BasicMOSSProvider
from ghostiss.core.moss.modules import BasicModulesProvider
from ghostiss.contracts.storage import Storage, FileStorageProvider
from ghostiss.contracts.configs import ConfigsByStorageProvider
from ghostiss.framework.llms import ConfigBasedLLMsProvider
from ghostiss.framework.llms.test_case import ChatCompletionTestCase, run_test_cases
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.json import JSON
from pydantic import BaseModel

# todo: remove scripted test to configured test

def prepare_container() -> Container:
    container = Container()
    ghostiss_dir = os.path.abspath(os.path.dirname(__file__) + "/../../demo/ghostiss")

    container.register(FileStorageProvider(ghostiss_dir))
    container.register(ConfigsByStorageProvider("configs"))
    container.register(ConfigBasedLLMsProvider("llms/llms_conf.yaml"))

    container.register(BasicMOSSProvider())
    container.register(BasicModulesProvider())

    return container



def testmoss_baseline():
    def foo() -> str:
        return "foo"

    class Bar(BaseModel):
        x: int
        y: int

        def bar(self) -> int:
            return self.x + self.y

    c = prepare_container()
    moss = c.force_fetch(MOSS)
    # 创造一个带reflection的moss实例
    m = moss.new(foo, Bar)
    prompt = m.dump_code_prompt()
    assert "def foo() -> str" in prompt
    assert "class Bar(BaseModel" in prompt

    code = """
result: str = ""
result = os.foo()
    """

    r = m(code=code, target='result')
    assert r == "foo"
    m.destroy()

    # 尝试运行一个 code 定义的函数.
    m = moss.new(foo, Bar)
    code = """
def main(os: MOSS) -> str:
    return os.foo()
    """
    r = m(code=code, target='main', args=['os'])
    assert r == "foo"


def testmoss_basic_method():

    class Future(BaseModel):
        """
        一个可以观测的结果.
        """
        id: str
        name: str
        descr: str

    def get_weather(city: str, date: datetime.date) -> Future:
        """
        获取一个城市的天气.
        """
        dct = {"beijing": Future(id=1, name="rainy", descr="rainy")}

        return dct[city]

    c = prepare_container()
    moss = c.force_fetch(MOSS)
    m = moss.new(Future, get_weather)
    prompt = m.dump_code_prompt()
    print(prompt)
    code = """
def main(os: MOSS) -> Future:
    return os.get_weather()
    """
    r = m(code=code, target='result')
    print(r)


def testmoss_multi_methods():

    query = "I want to watch a movie this Sunday (not today) evening at 9 PM. Find the nearest cinema and the best movie for me, then book the movie ticket directly for me."

    import random
    from pydantic import BaseModel
    from datetime import datetime

    class Movie(BaseModel):
        movie_id: str
        title: str
        ratings: float

    class Cinema(BaseModel):
        cinema_id: str
        name: str
        address: str
        distance: float  # Distance from the user in kilometers

    class TicketInfo(BaseModel):
        movie_title: str
        cinema_name: str
        time: str
        seat: str

    def get_day_of_week_as_number(time: datetime) -> int:
        """get the day of week (1 --- 7) when given time"""
        return 5

    def get_current_all_movies() -> List[Movie]:
        """Return a list of movies currently playing in cinemas."""
        return [
            Movie(movie_id="tt0111161", title="The Shawshank Redemption", ratings=9.3),
            Movie(movie_id="tt0068646", title="The Godfather", ratings=9.2),
            Movie(movie_id="tt0468569", title="The Dark Knight", ratings=9.0),
        ]

    def get_cinemas() -> List[Cinema]:
        """Return a list of cinemas with their locations."""
        return [
            Cinema(cinema_id="cin01", name="Cinema Paris Centre", address="Downtown Paris", distance=2.5),
            Cinema(cinema_id="cin02", name="Cinema Paris North", address="North Paris", distance=5.0),
        ]

    def get_the_most_recommend_movie_for_me(movies: List[Movie]) -> Movie:
        """Select a movie based on ratings and builtin-personalized information."""
        # For demonstration, we'll simply select the highest rated movie
        return max(movies, key=lambda x: x.ratings)

    def find_nearest_cinema(cinemas):
        """Return the nearest cinema based on distance."""
        return min(cinemas, key=lambda x: x.distance)

    def book_ticket(movie: Movie, cinema: Cinema, time: datetime) -> TicketInfo:
        """Book a ticket for a specified movie at a specified cinema."""
        seats = ['A1', 'A2', 'A3', 'A4', 'A5']
        chosen_seat = random.choice(seats)
        return TicketInfo(
            movie_title=movie.title,
            cinema_name=cinema.name,
            time=time,
            seat=chosen_seat
        )

    c = prepare_container()
    moss = c.force_fetch(MOSS)
    # 创造一个带reflection的moss实例
    m = moss.new(Movie, Cinema, TicketInfo, get_day_of_week_as_number, get_current_all_movies, get_cinemas,
                 get_the_most_recommend_movie_for_me, find_nearest_cinema, book_ticket)
    prompt = m.dump_code_prompt()
    print(prompt)


