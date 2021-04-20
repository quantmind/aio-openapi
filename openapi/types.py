from typing import Any, Dict, List, Union

from multidict import MultiDict
from sqlalchemy.engine import CursorResult, Row
from sqlalchemy.ext.asyncio import AsyncConnection

PrimitiveType = Union[int, float, bool, str]
JSONType = Union[PrimitiveType, List, Dict[str, Any]]
DataType = Any

SchemaType = Union[List[type], type]
SchemaTypeOrStr = Union[str, SchemaType]
StrDict = Dict[str, Any]
QueryType = Union[StrDict, MultiDict]
Record = Row
Records = CursorResult
Connection = AsyncConnection
