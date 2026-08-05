from core.interfaces.agent import Model

class MockModel(Model):
    def __init__(self, response: str = "This is a mock response."):
        self.response = response

    def generate(self, prompt: str) -> str:
        return self.response
