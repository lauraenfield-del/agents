import pytest
import os
# import shutil  <- Ignore the Mac-specific error, as it's not used in this project
from core.memory.simple import SimpleMemory
from core.memory.file import FileMemory

@pytest.fixture(params=[SimpleMemory, FileMemory])
def memory_impl(request, tmpdir):
    if request.param == SimpleMemory:
        return SimpleMemory()
    elif request.param == FileMemory:
        # Create a temporary directory for file-based memory tests
        mem_dir = os.path.join(str(tmpdir), 'file_memory')
        return FileMemory(base_directory=mem_dir)

def test_store_and_retrieve(memory_impl):
    memory_impl.store("foo", "bar")
    assert memory_impl.retrieve("foo") == "bar"

    memory_impl.store("baz", {"a": 1, "b": [2, 3]})
    assert memory_impl.retrieve("baz") == {"a": 1, "b": [2, 3]}

def test_delete(memory_impl):
    memory_impl.store("to_delete", "value")
    assert memory_impl.retrieve("to_delete") == "value"
    memory_impl.delete("to_delete")
    assert memory_impl.retrieve("to_delete") is None

def test_list_keys(memory_impl):
    # Clear memory before test
    for key in memory_impl.list_keys():
        memory_impl.delete(key)
        
    keys = memory_impl.list_keys()
    assert len(keys) == 0

    memory_impl.store("key1", "val1")
    memory_impl.store("key2", "val2")
    
    keys = sorted(memory_impl.list_keys())
    assert keys == ["key1", "key2"]
