class InvalidTypeException(Exception):
    def __init__(self, field):
        super().__init__(f"Cannot parse field {field.name} of type {field.type}")


class InvalidSpecException(Exception):
    def __init__(self, message):
        super().__init__(message)
