from typing import Any, Dict, List, Union

from asyncpg import Record
from multidict import MultiDict

PrimitiveType = Union[int, float, bool, str]
JSONType = Union[PrimitiveType, List, Dict[str, Any]]
DataType = Any

SchemaType = Union[List[type], type]
SchemaTypeOrStr = Union[str, SchemaType]
StrDict = Dict[str, Any]
QueryType = Union[StrDict, MultiDict]
Records = List[Record]
