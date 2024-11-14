from ghostos.core.messages import MessageKindParser, VariableMessage
from ghostos.framework.variables import test_variables
from pydantic import BaseModel


def test_message_parser():
    parser = MessageKindParser(test_variables)
    messages = list(parser.parse(['Hello World']))
    assert len(messages) == 1
    assert messages[0].content == 'Hello World'


class Foo(BaseModel):
    foo: str = "hello"


def test_variable_message():
    parser = MessageKindParser(test_variables)
    messages = list(parser.parse([Foo()]))
    assert len(messages) > 0

    message = messages[0]
    var = VariableMessage.from_message(message)
    assert var is not None
    value = test_variables.load(var.attrs.vid)
    assert value.foo == "hello"
