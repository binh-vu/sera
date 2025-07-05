from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, TypeGuard, TypeVar, Union

import msgspec


class doc(str):
    """A docstring for a type. Typically used in Annotated"""


T = TypeVar("T")
FieldName = Annotated[str, doc("field name of a class")]
ObjectPath = Annotated[
    str, doc("path of an object (e.g., can be function, class, etc.)")
]


class Language(str, Enum):
    Python = "python"
    Typescript = "typescript"


# re-export msgspec.UnsetType & msgspec.UNSET, so that we are consistent with ORM & data modules
UnsetType = msgspec.UnsetType
UNSET: Any = msgspec.UNSET


def is_set(value: Union[T, UnsetType]) -> TypeGuard[T]:
    """Typeguard to check if a value is set (not UNSET)"""
    return value is not UNSET


# Global identifiers for codegen
GLOBAL_IDENTS = {
    "AsyncSession": "sqlalchemy.ext.asyncio.AsyncSession",
    "ASGIConnection": "litestar.connection.ASGIConnection",
    "UNSET": "sera.typing.UNSET",
    "ForeignKey": "sqlalchemy.ForeignKey",
}
