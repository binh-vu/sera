from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Literal

PyDataType = Literal["str", "int", "datetime", "float", "bool", "bytes", "dict"]
TypescriptDataType = Literal["string", "number", "boolean"]
SQLAlchemyDataType = Literal[
    "String",
    "Integer",
    "Float",
    "Boolean",
    "DateTime",
    "JSON",
    "Text",
    "LargeBinary",
]


@dataclass
class TypeWithDep:
    type: str
    dep: str | None = None


@dataclass
class PyTypeWithDep(TypeWithDep):

    def get_python_type(self) -> type:
        """Get the Python type from the type string for typing annotation in Python."""
        if self.type == "str":
            return str
        elif self.type == "int":
            return int
        elif self.type == "float":
            return float
        elif self.type == "bool":
            return bool
        elif self.type == "bytes":
            return bytes
        elif self.type == "dict":
            return dict
        elif self.type == "datetime":
            return datetime.datetime
        else:
            raise ValueError(f"Unknown type: {self.type}")


@dataclass
class DataType:
    pytype: PyDataType
    sqltype: SQLAlchemyDataType
    tstype: TypescriptDataType

    is_list: bool = False

    def get_python_type(self) -> TypeWithDep:
        if self.pytype in ["str", "int", "float", "bool", "bytes", "dict"]:
            return TypeWithDep(type=self.pytype)
        if self.pytype == "datetime":
            return TypeWithDep(type="datetime", dep="datetime.datetime")
        raise NotImplementedError(self.pytype)

    def get_sqlalchemy_type(self) -> TypeWithDep:
        if self.pytype in ["str", "int", "float", "bool", "bytes"]:
            return TypeWithDep(type=self.pytype)
        if self.pytype == "dict":
            return TypeWithDep(type="JSON")
        if self.pytype == "datetime":
            return TypeWithDep(type="datetime", dep="datetime.datetime")
        raise NotImplementedError(self.pytype)


predefined_datatypes = {
    "string": DataType(pytype="str", sqltype="String", tstype="string", is_list=False),
    "integer": DataType(
        pytype="int", sqltype="Integer", tstype="number", is_list=False
    ),
    "datetime": DataType(
        pytype="datetime", sqltype="DateTime", tstype="string", is_list=False
    ),
    "float": DataType(pytype="float", sqltype="Float", tstype="number", is_list=False),
    "boolean": DataType(
        pytype="bool", sqltype="Boolean", tstype="boolean", is_list=False
    ),
    "bytes": DataType(
        pytype="bytes", sqltype="LargeBinary", tstype="string", is_list=False
    ),
    "dict": DataType(pytype="dict", sqltype="JSON", tstype="string", is_list=False),
}
