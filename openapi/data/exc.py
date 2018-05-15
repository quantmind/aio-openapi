from dataclasses import dataclass


@dataclass
class Error:
    field: str
    message: str

    @classmethod
    def from_errors(cls, errors):
        return errors
