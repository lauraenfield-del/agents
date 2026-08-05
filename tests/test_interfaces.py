import pytest
from core.interfaces.agent import Agent, Tool, Memory

def test_agent_interface():
    class MyAgent(Agent):
        def run(self, *args, **kwargs):
            return "Running"

    agent = MyAgent()
    assert agent.run() == "Running"

    with pytest.raises(TypeError):
        class BadAgent(Agent):
            pass
        BadAgent()

def test_tool_interface():
    class MyTool(Tool):
        def execute(self, *args, **kwargs):
            return "Executing"

    tool = MyTool()
    assert tool.execute() == "Executing"

    with pytest.raises(TypeError):
        class BadTool(Tool):
            pass
        BadTool()

def test_memory_interface():
    class MyMemory(Memory):
        def __init__(self):
            self.data = {}
        def store(self, key, value):
            self.data[key] = value
        def retrieve(self, key):
            return self.data.get(key)

    memory = MyMemory()
    memory.store("foo", "bar")
    assert memory.retrieve("foo") == "bar"

    with pytest.raises(TypeError):
        class BadMemory(Memory):
            def store(self, key, value):
                pass
        BadMemory()
