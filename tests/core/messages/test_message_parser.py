from ghostos.core.messages import MessageKindParser


def test_message_parser():
    parser = MessageKindParser()
    messages = list(parser.parse(['Hello World']))
    assert len(messages) == 1
    assert messages[0].content == 'Hello World'
