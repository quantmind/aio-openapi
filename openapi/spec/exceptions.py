class InvalidTypeException(Exception):

    def __init__(self, field_type):
        super().__init__(f'Cannot parse type {field_type}')


class InvalidFieldException(Exception):

    def __init__(self, field, message):
        self.field = field
        message += f' ({field.name})'
        super().__init__(message)


class InvalidPathException(Exception):

    def __init__(self, path, message):
        self.path = path
        message += f' ({path})'
        super().__init__(message)


class InvalidMethodException(Exception):

    def __init__(self, method, message):
        self.method = method
        message += f' ({method})'
        super().__init__(message)


class InvalidTagException(Exception):

    def __init__(self, tag, message):
        self.tag = tag
        message += f' ({tag})'
        super().__init__(message)
