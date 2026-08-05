import os
import re
import json
from typing import List, Any
from core.interfaces.agent import Memory

class FileMemory(Memory):
    def __init__(self, base_directory: str):
        self.base_directory = base_directory
        if not os.path.exists(self.base_directory):
            os.makedirs(self.base_directory)

    def _sanitize_key(self, key: str) -> str:
        # Remove invalid filename characters
        key = re.sub(r'[^a-zA-Z0-9_.-]', '_', key)
        return key

    def _get_path(self, key: str) -> str:
        return os.path.join(self.base_directory, self._sanitize_key(key) + ".json")

    def store(self, key: str, value: Any):
        path = self._get_path(key)
        with open(path, 'w') as f:
            json.dump(value, f)

    def retrieve(self, key: str) -> Any:
        path = self._get_path(key)
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            return json.load(f)

    def delete(self, key: str):
        path = self._get_path(key)
        if os.path.exists(path):
            os.remove(path)

    def list_keys(self) -> List[str]:
        keys = []
        for filename in os.listdir(self.base_directory):
            if filename.endswith(".json"):
                keys.append(os.path.splitext(filename)[0])
        return keys
