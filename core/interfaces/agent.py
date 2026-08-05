from abc import ABC, abstractmethod

class Agent(ABC):
    @abstractmethod
    def run(self, *args, **kwargs):
        pass

class Tool(ABC):
    @abstractmethod
    def execute(self, *args, **kwargs):
        pass

class Memory(ABC):
    @abstractmethod
    def store(self, key, value):
        pass

    @abstractmethod
    def retrieve(self, key):
        pass
