from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from codegen.models import expr

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
        type = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "bytes": bytes,
            "dict": dict,
            "datetime": datetime.datetime,
            "list[str]": list[str],
            "list[int]": list[int],
            "list[float]": list[float],
            "list[bool]": list[bool],
            "list[bytes]": list[bytes],
            "list[dict]": list[dict],
            "list[datetime]": list[datetime.datetime],
        }.get(self.type, None)
        if type is None:
            raise ValueError(f"Unknown type: {self.type}")
        return type

    def as_list_type(self) -> PyTypeWithDep:
        """Convert the type to a list type."""
        return PyTypeWithDep(type=f"list[{self.type}]", dep=self.dep)


@dataclass
class TsTypeWithDep(TypeWithDep):

    def get_default(self) -> expr.ExprConstant:
        if self.type.endswith("[]"):
            return expr.ExprConstant([])
        if self.type == "string":
            return expr.ExprConstant("")
        if self.type == "number":
            return expr.ExprConstant(0)
        if self.type == "boolean":
            return expr.ExprConstant(False)
        raise ValueError(f"Unknown type: {self.type}")

    def as_list_type(self) -> TsTypeWithDep:
        return TsTypeWithDep(type=f"{self.type}[]", dep=self.dep)


@dataclass
class DataType:
    pytype: PyDataType
    sqltype: SQLAlchemyDataType
    tstype: TypescriptDataType

    is_list: bool = False

    def get_python_type(self) -> PyTypeWithDep:
        if self.pytype in ["str", "int", "float", "bool", "bytes", "dict"]:
            pytype = PyTypeWithDep(type=self.pytype)
        elif self.pytype == "datetime":
            pytype = PyTypeWithDep(type=self.pytype, dep="datetime.datetime")
        else:
            raise NotImplementedError(self.pytype)

        if self.is_list:
            return pytype.as_list_type()
        return pytype

    def get_sqlalchemy_type(self) -> TypeWithDep:
        if self.pytype in ["str", "int", "float", "bool", "bytes"]:
            return TypeWithDep(type=self.pytype)
        if self.pytype == "dict":
            return TypeWithDep(type="JSON")
        if self.pytype == "datetime":
            return TypeWithDep(type="datetime", dep="datetime.datetime")
        raise NotImplementedError(self.pytype)

    def get_typescript_type(self) -> TsTypeWithDep:
        if self.tstype in ["string", "number", "boolean"]:
            tstype = TsTypeWithDep(type=self.tstype)
        else:
            raise NotImplementedError(self.tstype)
        if self.is_list:
            return tstype.as_list_type()
        return tstype


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
