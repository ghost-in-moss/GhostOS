import sys
from os.path import dirname

# I hate python imports
ghostos_project_dir = dirname(dirname(__file__))
sys.path.append(ghostos_project_dir)

from ghostos.bootstrap import ghost_func


@ghost_func.decorator(caching=False)
def get_weather(city: str, date: str) -> str:
    """
    搜寻一个城市在给定日期的天气.
    :param city: 城市名
    :param date: 日期
    :return: 关于天气的自然语言描述
    """
    # 你的任务是, 先观察用户输入的 city, date 是什么, 确定了它的值, 再输出真正的函数.
    # 然后 mock 一个自然语言的天气描述结果, 用自然语言返回. 你使用的语言必须要和入参语种一致.
    pass


if __name__ == "__main__":
    # the llms will generate dynamic codes for this function and execute them through Moss
    # this is a toy for Moss testing, but notice it still cast LLM tokens...
    print(get_weather("beijing", "today"))
