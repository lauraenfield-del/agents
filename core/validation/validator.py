from jsonschema import validate
from jsonschema.exceptions import ValidationError

class Validator:
    @staticmethod
    def validate(instance: dict, schema: dict) -> bool:
        try:
            validate(instance=instance, schema=schema)
            return True
        except ValidationError as e:
            # Optionally, you could log the validation error here
            return False
