from ghostos_moss import Moss as Parent
from ghostos.libraries.replier import Replier


def sqrt_newton(n, epsilon=1e-7):
    """
    使用牛顿迭代法计算平方根
    :param n: 要计算平方根的数
    :param epsilon: 迭代精度
    :return: 平方根的近似值
    """
    if n < 0:
        raise ValueError("Cannot compute square root of a negative number")
    x = n
    while abs(x * x - n) > epsilon:
        x = (x + n / x) / 2
    return x


class Moss(Parent):
    replier: Replier


# <moss-hide>
from ghostos.ghosts.moss_agent import MossAgent

# the __ghost__ magic attr define a ghost instance
# so the script `ghostos web` or `ghostos console` can detect it
# and run agent application with this ghost.
__ghost__ = MossAgent(
    id=__name__,
    moss_module=__name__,
    name="jojo",
    description="a chatbot for baseline test",
    persona="you are an LLM-driven cute girl, named jojo",
    instruction="remember talk to user with user's language.",
    # set model using openai-o1
    llm_api="deepseek-reasoner",
)
# </moss-hide>
