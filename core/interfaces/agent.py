from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.tools.manager import ToolManager
    from core.interfaces.agent import Memory, Model

class Agent(ABC):
    tools: Optional["ToolManager"] = None
    memory: Optional["Memory"] = None
    model: Optional["Model"] = None

    @abstractmethod
    def run(self, *args, **kwargs):
        pass

class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def schema(self) -> dict:
        pass

    @abstractmethod
    def execute(self, *args, **kwargs):
        pass

class Memory(ABC):
    @abstractmethod
    def store(self, key: str, value: any):
        pass

    @abstractmethod
    def retrieve(self, key: str) -> any:
        pass

    @abstractmethod
    def delete(self, key: str):
        pass

    @abstractmethod
    def list_keys(self) -> list[str]:
        pass

class Model(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

class Workflow(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def run(self, agent: "Agent"):
        pass
