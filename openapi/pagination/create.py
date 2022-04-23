from typing import Optional, Type, TypeVar

from ..utils import TypingInfo
from .pagination import Pagination
from .search import Search

T = TypeVar("T")

CREATE_MAP = {Pagination: "create_pagination", Search: "create_search"}


def create_dataclass(
    type_info: Optional[TypingInfo], data: dict, DataClass: Type[T]
) -> T:
    if type_info is None:
        return DataClass()
    if type_info.is_dataclass and issubclass(type_info.element, DataClass):
        method_name = CREATE_MAP.get(DataClass)
        if method_name:
            return getattr(type_info.element, method_name)(data)
    return DataClass()
