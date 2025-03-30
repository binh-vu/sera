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
            "str[]": list[str],
            "int[]": list[int],
            "float[]": list[float],
            "bool[]": list[bool],
            "bytes[]": list[bytes],
            "dict[]": list[dict],
            "datetime[]": list[datetime.datetime],
        }.get(self.type, None)
        if type is None:
            raise ValueError(f"Unknown type: {self.type}")
        return type


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


@dataclass
class DataType:
    pytype: PyDataType
    sqltype: SQLAlchemyDataType
    tstype: TypescriptDataType

    is_list: bool = False

    def get_python_type(self) -> TypeWithDep:
        if self.pytype in ["str", "int", "float", "bool", "bytes", "dict"]:
            pytype = self.pytype
            if self.is_list:
                pytype = f"list[{pytype}]"
            return TypeWithDep(type=pytype)
        if self.pytype == "datetime":
            pytype = self.pytype
            if self.is_list:
                pytype = f"list[{pytype}]"
            return TypeWithDep(type=pytype, dep="datetime.datetime")
        raise NotImplementedError(self.pytype)

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
            tstype = self.tstype
            if self.is_list:
                tstype = f"{tstype}[]"
            return TsTypeWithDep(type=tstype)
        raise NotImplementedError(self.tstype)


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
