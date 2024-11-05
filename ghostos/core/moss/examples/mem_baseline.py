from ghostos.core.moss.abc import Moss as Parent, attr
from ghostos.mocks.libraries.auto_text_memory import Mem0TextMemory
from ghostos.framework.libraries.auto_memory import ProxyConfig


class Moss(Parent):
    """
    本地定义的 Moss 类. 每个 MOSS 文件里都应该有一个 Moss 类, 可以是 import 的也可以是本地定义的.
    记得它要继承自 Moss.
    """
    text_memory: Mem0TextMemory


# <moss-hide>

def test_main(moss: Moss) -> int:
    """
    模拟一个 main 方法, 测试 moss 的调用.
    assert 返回值是 3. 外部的 MOSSRuntime 调用这个方法.
    """
    import os

    openai_proxy = os.environ.get('OPENAI_PROXY')
    if openai_proxy:
        moss.text_memory = Mem0TextMemory(proxy_config=ProxyConfig(proxy_url=openai_proxy))
    else:
        moss.text_memory = Mem0TextMemory()

    m = moss.text_memory
    # 1. Add: Store a memory from any unstructured text
    result = m.add("I am working on improving my tennis skills. Suggest some online courses.", agent_id="alice")
    print(result)
    all_memories = m.get_all()
    memory_id = all_memories[0]["id"]  # get a memory_id

    # Created memory --> 'Improving her tennis skills.' and 'Looking for online suggestions.'

    # 2. Update: update the memory
    result = m.update(memory_id=memory_id, data="Likes to play tennis on weekends")
    print(result)

    # Updated memory --> 'Likes to play tennis on weekends.' and 'Looking for online suggestions.'

    # 3. Search: search related memories
    related_memories = m.search(query="What are Alice do on weekends ?", agent_id="alice")
    print(related_memories)

    # 5. Get memory history for a particular memory_id
    history = m.history(memory_id=memory_id)
    print(history)

# </moss-hide>


if __name__ == "__main__":
    test_main(Moss())

