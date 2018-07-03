from dataclasses import dataclass
from typing import List

from .fields import data_field


@dataclass
class FieldError:
    """Error message for a data field
    """
    field: str = data_field(description='name of the data field with error')
    message: str = data_field(description='error message')


@dataclass
class Error:
    """Error message and list of errors for data fields
    """
    message: str = data_field(description='error message')
    errors: List[FieldError]
