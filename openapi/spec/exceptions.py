class InvalidTypeException(Exception):

    def __init__(self, field_type):
        message = 'Cannot parse type %s' % field_type
        super().__init__(message)
