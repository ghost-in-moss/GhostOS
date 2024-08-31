from .mock_code import MockClass

class AnotherMockClass:
    def __init__(self):
        self.mock_instance = MockClass()

    def another_mock_method(self):
        return self.mock_instance.mock_method()

ANOTHER_MOCK_CONSTANT = "This is another mock constant"

def another_mock_function(value):
    return f"Processed: {value}"