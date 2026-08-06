import pytest
from core.validation.validator import Validator

@pytest.fixture
def schema():
    return {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string", "format": "email"},
        },
        "required": ["name", "email"],
    }

def test_valid_instance(schema):
    instance = {"name": "John Doe", "email": "john.doe@example.com"}
    assert Validator.validate(instance, schema) is True

def test_invalid_instance_missing_required(schema):
    instance = {"name": "John Doe"}
    assert Validator.validate(instance, schema) is False

def test_invalid_instance_wrong_type(schema):
    instance = {"name": 123, "email": "john.doe@example.com"}
    assert Validator.validate(instance, schema) is False
