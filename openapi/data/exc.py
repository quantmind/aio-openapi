from dataclasses import dataclass
from typing import List

from .fields import data_field


@dataclass
class ErrorMessage:
    """Error message and list of errors for data fields
    """
    message: str = data_field(description='Error message')


@dataclass
class FieldError(ErrorMessage):
    """Error message for a data field
    """
    field: str = data_field(description='name of the data field with error')


@dataclass
class ValidationErrors(ErrorMessage):
    """Error message and list of errors for data fields
    """
    errors: List[FieldError] = data_field(description='List of field errors')


def error_response_schema(status):
    return ValidationErrors if status == 422 else ErrorMessage
