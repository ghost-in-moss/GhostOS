from ghostos.framework.llms import PromptStorageImpl, Prompt
from ghostos.framework.storage import MemStorage
from ghostos.core.messages import Message


def test_prompt_storage_baseline():
    storage = MemStorage()
    prompts = PromptStorageImpl(storage)

    prompt = Prompt()
    prompt.inputs.append(Message.new_tail(content="hello world"))
    id_ = prompt.id

    prompts.save(prompt)
    got = prompts.get(id_)
    assert got.inputs == prompt.inputs
    assert got.id == prompt.id
    assert got == prompt
