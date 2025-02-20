from ghostos.ghosts import Chatbot
from ghostos_common.identifier import get_identifier


def test_chatbot_has_identifier():
    chatbot = Chatbot(name="test")
    identifier = get_identifier(chatbot)
    assert identifier.name == "test"
