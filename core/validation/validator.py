from jsonschema import validate
from jsonschema.exceptions import ValidationError

class Validator:
    @staticmethod
    def validate(instance: dict, schema: dict):
        try:
            validate(instance=instance, schema=schema)
        except ValidationError as e:
            raise ValueError(f"Invalid arguments: {e.message}") from e
