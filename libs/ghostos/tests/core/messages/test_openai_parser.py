from ghostos.core.messages.openai import DefaultOpenAIMessageParser
from openai.types.chat.chat_completion_chunk import (
    ChatCompletionChunk, Choice, ChoiceDelta,
    ChoiceDeltaToolCall, ChoiceDeltaToolCallFunction,
)
from ghostos.core.messages.message import MessageType
from ghostos.core.messages.pipeline import SequencePipe, run_pipeline
from ghostos.core.messages.transport import new_basic_connection


def test_openai_parser_bad_case_1():
    items = [
        ChatCompletionChunk(id='chatcmpl-AXs0YM2VxVZbo50C1lIOC0qlWumtN', choices=[
            Choice(delta=ChoiceDelta(content='。', fuction_call=None, refusal=None, role=None, tool_calls=None),
                   finish_reason=None, index=0, logprobs=None)], created=1732635794, model='gpt-4o-2024-08-06',
                            object='chat.completion.chunk', service_tier=None, system_fingerprint='fp_831e067d82',
                            usage=None),
        ChatCompletionChunk(id='chatcmpl-AXs0YM2VxVZbo50C1lIOC0qlWumtN', choices=[Choice(
            delta=ChoiceDelta(content=None, function_call=None, refusal=None, role=None, tool_calls=[
                ChoiceDeltaToolCall(index=0, id='call_DCaC3PJy336sZ9ryhxijgFlq',
                                    function=ChoiceDeltaToolCallFunction(arguments='', name='moss'), type='function')]),
            finish_reason=None, index=0, logprobs=None)], created=1732635794, model='gpt-4o-2024-08-06',
                            object='chat.completion.chunk', service_tier=None, system_fingerprint='fp_831e067d82',
                            usage=None),
        ChatCompletionChunk(
            id='chatcmpl-AXs0YM2VxVZbo50C1lIOC0qlWumtN',
            choices=[Choice(
                delta=ChoiceDelta(
                    content=None, function_call=None, refusal=None, role=None,
                    tool_calls=[
                        ChoiceDeltaToolCall(
                            index=0, id=None,
                            function=ChoiceDeltaToolCallFunction(
                                arguments='{"',
                                name=None,
                            ),
                            type=None)
                    ]),
                finish_reason=None,
                index=0,
                logprobs=None
            ), ],
            created=1732635794,
            model='gpt-4o-2024-08-06',
            object='chat.completion.chunk',
            service_tier=None,
            system_fingerprint='fp_831e067d82',
            usage=None,
        )
    ]
    parser = DefaultOpenAIMessageParser(None, None)
    pipes = [SequencePipe(), SequencePipe(), SequencePipe()]
    messages = parser.from_chat_completion_chunks(items)
    messages = list(run_pipeline(pipes, messages))
    assert len(messages) == len(items) + 2

    stream, receiver = new_basic_connection()
    with stream:
        stream.send(messages)
    with receiver:
        got = receiver.wait()
        assert len(got) == 2
    assert got[0].get_unique_id() != got[1].get_unique_id()
    assert got[0].type == ""
    assert got[1].type == MessageType.FUNCTION_CALL
