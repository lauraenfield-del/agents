from typing import Dict, List, Any
from core.interfaces.agent import Memory

class SimpleMemory(Memory):
    def __init__(self):
        self._data: Dict[str, Any] = {}

    def store(self, key: str, value: Any):
        self._data[key] = value

    def retrieve(self, key: str) -> Any:
        return self._data.get(key)

    def delete(self, key: str):
        if key in self._data:
            del self._data[key]

    def list_keys(self) -> List[str]:
        return list(self._data.keys())
