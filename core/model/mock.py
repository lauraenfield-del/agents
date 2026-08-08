from core.interfaces.agent import Model

class MockModel(Model):
    def __init__(self, response: str | None = None):
        self.response = response

    def generate(self, prompt: str) -> str:
        if self.response is not None:
            return self.response
        return prompt
