import inspect
from ghostiss.core.moss2 import prompts
from ghostiss.core.moss2.prompts import reflect_module_locals, compile_attr_prompts


def test_prompts_baseline():
    assert inspect.ismodule(prompts)
    # inspect 也被 prompts 库引用了.
    assert not inspect.isbuiltin(inspect)
    attr_prompts = reflect_module_locals("ghostiss.core.moss2.prompts", prompts.__dict__)
    data = {}
    array = []
    for name, prompt in attr_prompts:
        array.append((name, prompt))
        data[name] = prompt
    # 从 utils 模块里定义的.
    assert "is_typing" in data
    # typing 库本身的不会出现.
    assert "Optional" not in data
    # 引用的抽象类应该存在.
    assert "PromptAble" in data

    prompt = compile_attr_prompts(array)
    assert "class PromptAble" in prompt
