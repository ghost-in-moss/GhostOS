from ghostos.core.moss.prompts import get_prompt
from ghostos.core.ghosts.thoughts import Thought, ModelThought


def test_get_prompt_from_thought():
    prompt = get_prompt(Thought)
    assert prompt == Thought.__class_prompt__()


def test_get_prompt_from_thought_with_no_thought():
    prompt = get_prompt(ModelThought)
    assert prompt == ModelThought.__class_prompt__()

    class TestThought(ModelThought):
        foo: int = 123

    prompt = get_prompt(TestThought)
    assert "class TestThought" in prompt
