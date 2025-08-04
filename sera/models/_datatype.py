from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Callable, Literal

from codegen.models import expr

from sera.misc import identity

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
    deps: list[str] = field(default_factory=list)

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
        return PyTypeWithDep(type=f"list[{self.type}]", deps=self.deps)

    def as_optional_type(self) -> PyTypeWithDep:
        """Convert the type to an optional type."""
        if "typing.Optional" not in self.deps:
            deps = self.deps + ["typing.Optional"]
        else:
            deps = self.deps
        if "Optional[" in self.type:
            raise NotImplementedError(
                f"Have not handle nested optional yet: {self.type}"
            )
        return PyTypeWithDep(type=f"Optional[{self.type}]", deps=deps)

    def clone(self) -> PyTypeWithDep:
        """Clone the type with the same dependencies."""
        return PyTypeWithDep(type=self.type, deps=list(self.deps))

    def get_string_conversion_func(self) -> tuple[str, str]:
        if self.type == "str":
            return ("identity", "sera.misc.identity")
        if self.type == "int":
            return ("TypeConversion.to_int", "sera.libs.api_helper.TypeConversion")
        if self.type == "float":
            return ("TypeConversion.to_float", "sera.libs.api_helper.TypeConversion")
        if self.type == "bool":
            return ("TypeConversion.to_bool", "sera.libs.api_helper.TypeConversion")
        if any(
            dep.find(".models.enums.") != -1 and dep.endswith(self.type)
            for dep in self.deps
        ):
            # This is an enum type, we directly use the enum constructor as the conversion function
            return (
                self.type,
                [
                    dep
                    for dep in self.deps
                    if dep.find(".models.enums.") != -1 and dep.endswith(self.type)
                ][0],
            )
        else:
            raise NotImplementedError()


@dataclass
class TsTypeWithDep:
    type: str
    # the specific type of the value, to provide more details for the type because typescript use
    # number for both int and float, date for both date and datetime.
    spectype: str
    deps: list[str] = field(default_factory=list)

    def get_default(self) -> expr.ExprConstant:
        if self.type.endswith("[]"):
            return expr.ExprConstant([])
        if self.type == "string":
            return expr.ExprConstant("")
        if self.type == "number":
            return expr.ExprConstant(0)
        if self.type == "boolean":
            return expr.ExprConstant(False)
        if self.type == "Date":
            return expr.ExprConstant("new Date()")
        if self.type.endswith("| undefined"):
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
            list_spectype = f"({self.spectype})[]"
        else:
            list_type = f"{self.type}[]"
            list_spectype = f"{self.spectype}[]"
        return TsTypeWithDep(type=list_type, spectype=list_spectype, deps=self.deps)

    def as_optional_type(self) -> TsTypeWithDep:
        if "undefined" in self.type:
            raise NotImplementedError(
                f"Have not handle nested optional yet: {self.type}"
            )
        return TsTypeWithDep(
            type=f"{self.type} | undefined",
            # not changing the spectype because we convert to optional when the value is missing
            # spectype is used to tell the main type of the value when it is present.
            spectype=self.spectype,
            deps=self.deps,
        )

    def get_json_deser_func(self, value: expr.Expr) -> expr.Expr:
        """Get the typescript expression to convert the value from json format to the correct type."""
        if self.type in {"string", "number", "boolean", "string[]"}:
            return value
        if self.type == "Date":
            return expr.ExprRawTypescript(f"new Date({value.to_typescript()})")
        if any(x.startswith("@.models.enum") for x in self.deps):
            # enum type, we don't need to do anything as we use strings for enums
            return value
        raise ValueError(f"Unknown type: {self.type}")

    def get_json_ser_func(self, value: expr.Expr) -> expr.Expr:
        """Get the typescript expression to convert the value to json format."""
        if self.type in {
            "string",
            "number",
            "boolean",
            "string[]",
            "number | undefined",
            "boolean | undefined",
            "string | undefined",
        }:
            return value
        if self.type == "Date":
            return expr.ExprRawTypescript(f"{value.to_typescript()}.toISOString()")
        if self.type == "Date | undefined":
            return expr.ExprRawTypescript(f"{value.to_typescript()}?.toISOString()")
        if any(x.startswith("@.models.enum") for x in self.deps):
            # enum type, we don't need to do anything as we use strings for enums
            return value
        raise ValueError(f"Unknown type: {self.type}")


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

    def as_optional_type(self) -> SQLTypeWithDep:
        """Convert the type to an optional type."""
        if "typing.Optional" not in self.deps:
            deps = self.deps + ["typing.Optional"]
        else:
            deps = self.deps

        if "Optional[" in self.mapped_pytype:
            raise NotImplementedError(
                f"Have not handle nested optional yet: {self.mapped_pytype}"
            )
        return SQLTypeWithDep(
            type=self.type,
            mapped_pytype=f"Optional[{self.mapped_pytype}]",
            deps=deps,
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
        tstype=TsTypeWithDep(type="string", spectype="string"),
        is_list=False,
    ),
    "integer": DataType(
        pytype=PyTypeWithDep(type="int"),
        sqltype=SQLTypeWithDep(
            type="Integer", mapped_pytype="int", deps=["sqlalchemy.Integer"]
        ),
        tstype=TsTypeWithDep(type="number", spectype="integer"),
        is_list=False,
    ),
    "date": DataType(
        pytype=PyTypeWithDep(type="date", deps=["datetime.date"]),
        sqltype=SQLTypeWithDep(
            type="Date",
            mapped_pytype="date",
            deps=["sqlalchemy.Date", "datetime.date"],
        ),
        tstype=TsTypeWithDep(type="Date", spectype="date"),
        is_list=False,
    ),
    "datetime": DataType(
        pytype=PyTypeWithDep(type="datetime", deps=["datetime.datetime"]),
        sqltype=SQLTypeWithDep(
            type="DateTime",
            mapped_pytype="datetime",
            deps=["sqlalchemy.DateTime", "datetime.datetime"],
        ),
        tstype=TsTypeWithDep(type="Date", spectype="datetime"),
        is_list=False,
    ),
    "float": DataType(
        pytype=PyTypeWithDep(type="float"),
        sqltype=SQLTypeWithDep(
            type="Float", mapped_pytype="float", deps=["sqlalchemy.Float"]
        ),
        tstype=TsTypeWithDep(type="number", spectype="float"),
        is_list=False,
    ),
    "boolean": DataType(
        pytype=PyTypeWithDep(type="bool"),
        sqltype=SQLTypeWithDep(
            type="Boolean", mapped_pytype="bool", deps=["sqlalchemy.Boolean"]
        ),
        tstype=TsTypeWithDep(type="boolean", spectype="boolean"),
        is_list=False,
    ),
    "bytes": DataType(
        pytype=PyTypeWithDep(type="bytes"),
        sqltype=SQLTypeWithDep(
            type="LargeBinary", mapped_pytype="bytes", deps=["sqlalchemy.LargeBinary"]
        ),
        tstype=TsTypeWithDep(type="string", spectype="bytes"),
        is_list=False,
    ),
    "dict": DataType(
        pytype=PyTypeWithDep(type="dict"),
        sqltype=SQLTypeWithDep(
            type="JSON", mapped_pytype="dict", deps=["sqlalchemy.JSON"]
        ),
        tstype=TsTypeWithDep(type="string", spectype="dict"),
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
    "string": TsTypeWithDep(type="string", spectype="string"),
}
