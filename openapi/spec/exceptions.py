class InvalidTypeException(Exception):

    def __init__(self, field_type):
        super().__init__(f'Cannot parse type {field_type}')


class InvalidSpecException(Exception):

    def __init__(self, message):
        super().__init__(message)
