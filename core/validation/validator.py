from jsonschema import validate, FormatChecker
from jsonschema.exceptions import ValidationError

class Validator:
    @staticmethod
    def validate(instance: dict, schema: dict):
        try:
            validate(instance=instance, schema=schema, format_checker=FormatChecker())
        except ValidationError as e:
            raise ValueError(f"Invalid arguments: {e.message}") from e
