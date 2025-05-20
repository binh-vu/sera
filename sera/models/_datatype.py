from __future__ import annotations

import datetime
from dataclasses import dataclass, field
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
class PyTypeWithDep:
    type: str
    dep: str | None = None

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
class TsTypeWithDep:
    type: str
    dep: str | None = None

    def get_default(self) -> expr.ExprConstant:
        if self.type.endswith("[]"):
            return expr.ExprConstant([])
        if self.type == "string":
            return expr.ExprConstant("")
        if self.type == "number":
            return expr.ExprConstant(0)
        if self.type == "boolean":
            return expr.ExprConstant(False)
        if self.type == "string | undefined":
            return expr.ExprConstant("undefined")
        if self.type.endswith("| string)") or self.type.endswith("| string"):
            return expr.ExprConstant("")
        raise ValueError(f"Unknown type: {self.type}")

    def as_list_type(self) -> TsTypeWithDep:
        """Convert the type to a list type.
        If the type is not a simple identifier, wrap it in parentheses.
        """
        # Check if type is a simple identifier or needs parentheses
        if not all(c.isalnum() or c == "_" for c in self.type.strip()):
            # Type contains special chars like | or spaces, wrap in parentheses
            list_type = f"({self.type})[]"
        else:
            list_type = f"{self.type}[]"
        return TsTypeWithDep(type=list_type, dep=self.dep)


@dataclass
class SQLTypeWithDep:
    type: str
    mapped_pytype: str
    deps: list[str] = field(default_factory=list)

    def as_list_type(self) -> SQLTypeWithDep:
        """Convert the type to a list type."""
        return SQLTypeWithDep(
            type=f"ARRAY({self.type})",
            deps=self.deps + ["sqlalchemy.ARRAY"],
            mapped_pytype=f"list[{self.mapped_pytype}]",
        )


@dataclass
class DataType:
    pytype: PyTypeWithDep
    sqltype: SQLTypeWithDep
    tstype: TsTypeWithDep

    is_list: bool = False

    def get_python_type(self) -> PyTypeWithDep:
        pytype = self.pytype
        if self.is_list:
            return pytype.as_list_type()
        return pytype

    def get_sqlalchemy_type(self) -> SQLTypeWithDep:
        sqltype = self.sqltype
        if self.is_list:
            return sqltype.as_list_type()
        return sqltype

    def get_typescript_type(self) -> TsTypeWithDep:
        tstype = self.tstype
        if self.is_list:
            return tstype.as_list_type()
        return tstype


predefined_datatypes = {
    "string": DataType(
        pytype=PyTypeWithDep(type="str"),
        sqltype=SQLTypeWithDep(
            type="String", mapped_pytype="str", deps=["sqlalchemy.String"]
        ),
        tstype=TsTypeWithDep(type="string"),
        is_list=False,
    ),
    "optional[string]": DataType(
        pytype=PyTypeWithDep(type="Optional[str]", dep="typing.Optional"),
        sqltype=SQLTypeWithDep(
            type="String",
            mapped_pytype="Optional[str]",
            deps=["sqlalchemy.String", "typing.Optional"],
        ),
        tstype=TsTypeWithDep(type="string | undefined"),
        is_list=False,
    ),
    "integer": DataType(
        pytype=PyTypeWithDep(type="int"),
        sqltype=SQLTypeWithDep(
            type="Integer", mapped_pytype="int", deps=["sqlalchemy.Integer"]
        ),
        tstype=TsTypeWithDep(type="number"),
        is_list=False,
    ),
    "datetime": DataType(
        pytype=PyTypeWithDep(type="datetime", dep="datetime.datetime"),
        sqltype=SQLTypeWithDep(
            type="DateTime",
            mapped_pytype="datetime",
            deps=["sqlalchemy.DateTime", "datetime.datetime"],
        ),
        tstype=TsTypeWithDep(type="string"),
        is_list=False,
    ),
    "float": DataType(
        pytype=PyTypeWithDep(type="float"),
        sqltype=SQLTypeWithDep(
            type="Float", mapped_pytype="float", deps=["sqlalchemy.Float"]
        ),
        tstype=TsTypeWithDep(type="number"),
        is_list=False,
    ),
    "boolean": DataType(
        pytype=PyTypeWithDep(type="bool"),
        sqltype=SQLTypeWithDep(
            type="Boolean", mapped_pytype="bool", deps=["sqlalchemy.Boolean"]
        ),
        tstype=TsTypeWithDep(type="boolean"),
        is_list=False,
    ),
    "bytes": DataType(
        pytype=PyTypeWithDep(type="bytes"),
        sqltype=SQLTypeWithDep(
            type="LargeBinary", mapped_pytype="bytes", deps=["sqlalchemy.LargeBinary"]
        ),
        tstype=TsTypeWithDep(type="string"),
        is_list=False,
    ),
    "dict": DataType(
        pytype=PyTypeWithDep(type="dict"),
        sqltype=SQLTypeWithDep(
            type="JSON", mapped_pytype="dict", deps=["sqlalchemy.JSON"]
        ),
        tstype=TsTypeWithDep(type="string"),
        is_list=False,
    ),
}

predefined_py_datatypes = {"bytes": PyTypeWithDep(type="bytes")}
predefined_sql_datatypes = {
    "bit": SQLTypeWithDep(
        type="BIT", mapped_pytype="bytes", deps=["sqlalchemy.dialects.postgresql.BIT"]
    ),
}
predefined_ts_datatypes = {
    "string": TsTypeWithDep(type="string"),
}
