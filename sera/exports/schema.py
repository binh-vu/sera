from pathlib import Path
from typing import Dict, List, Optional

from sera.models import Cardinality, Class, DataProperty
from sera.models import (
    Enum as SeraModelsEnum,  # Alias to avoid conflict with Python's Enum if needed elsewhere
)
from sera.models import ObjectProperty, Schema, parse_schema

# Direct imports for specific model components
from sera.models._datatype import DataType
from sera.models._default import DefaultFactory
from sera.models._property import (  # ObjectPropDBInfo, # Not directly used in this function's logic beyond prop.db; DataPropDBInfo,   # Not directly used in this function's logic beyond prop.db; SystemControlledMode, # Not used; PropDataAttrs, # Not used
    ForeignKeyOnDelete,
    ForeignKeyOnUpdate,
)

# from sera.models._class import ClassDBMapInfo, Index # Not directly used beyond cls.db
# from sera.models._enum import EnumValue # Assuming values are strings based on error

# PRISMA_SCALAR_MAP = {
#     DataType.STRING: "String",
#     DataType.TEXT: "String",
#     DataType.INTEGER: "Int",
#     DataType.BIG_INTEGER: "BigInt",
#     DataType.FLOAT: "Float",
#     DataType.BOOLEAN: "Boolean",
#     DataType.DATETIME: "DateTime",
#     DataType.DATE: "DateTime",  # Prisma uses DateTime for Date as well
#     DataType.TIME: "DateTime",  # Prisma uses DateTime for Time
#     DataType.UUID: "String",  # Prisma typically maps UUID to String with @db.Uuid or relies on db default
#     DataType.JSON: "Json",
#     DataType.DECIMAL: "Decimal",
#     DataType.BYTES: "Bytes",
# }


def get_prisma_field_type(datatype: DataType) -> str:
    pytype = datatype.get_python_type().type
    if pytype == "str":
        return "String"
    if pytype == "int":
        return "Int"
    if pytype == "float":
        return "Float"
    if pytype == "bool":
        return "Boolean"
    if pytype == "bytes":
        return "Bytes"
    if pytype == "dict":
        return "Json"
    if pytype == "datetime":
        return "DateTime"
    if pytype == "list[str]":
        return "String[]"
    if pytype == "list[int]":
        return "Int[]"
    if pytype == "list[float]":
        return "Float[]"
    if pytype == "list[bool]":
        return "Boolean[]"
    if pytype == "list[bytes]":
        return "Bytes[]"
    if pytype == "list[dict]":
        return "Json[]"
    if pytype == "list[datetime]":
        return "DateTime[]"

    raise ValueError(f"Unsupported data type for Prisma: {pytype}")


def to_prisma_model(schema: Schema, cls: Class, lines: list[str]):
    """Convert a Sera Class to a Prisma model string representation."""
    lines.append(f"model {cls.name} {{")

    if cls.db is None:
        # This class has no database mapping, we must generate a default key for it
        lines.append("  _noid Int @id @default(autoincrement())")
    #     lines.append(f"  @@unique([%s])" % ", ".join(cls.properties.keys()))

    for prop in cls.properties.values():
        propattrs = ""
        if isinstance(prop, DataProperty):
            proptype = get_prisma_field_type(prop.datatype)
            if prop.is_optional:
                proptype = f"{proptype}?"
            if prop.db is not None and prop.db.is_primary_key:
                propattrs += "@id "
        else:
            proptype = "Int"

        lines.append(f"  {prop.name.ljust(30)} {proptype.ljust(10)} {propattrs}")

    lines.append("}\n")


def export_prisma_schema(schema: Schema, outfile: Path):
    """Export Prisma schema file"""
    lines = []

    # Datasource
    lines.append("datasource db {")
    lines.append(
        '  provider = "postgresql"'
    )  # Defaulting to postgresql as per user context
    lines.append('  url      = env("DATABASE_URL")')
    lines.append("}\n")

    # Generator
    lines.append("generator client {")
    lines.append('  provider = "prisma-client-py"')
    lines.append("  recursive_type_depth = 5")
    lines.append("}\n")

    # Enums
    if schema.enums:
        for enum_name, enum_def in schema.enums.items():
            lines.append(f"enum {enum_name} {{")
            # Assuming enum_def.values is a list of strings based on previous errors
            for val_str in enum_def.values:
                lines.append(f"  {val_str}")
            lines.append("}\\n")

    # Models
    for cls in schema.topological_sort():
        to_prisma_model(schema, cls, lines)

    with outfile.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    PROJECT_DIR = Path("/Users/binhvu/workspace/workspace/projects/ridge")

    schema = parse_schema(
        "ridge",
        [
            PROJECT_DIR / "user/schema/user.yml",
            PROJECT_DIR / "user/schema/tenant.yml",
            PROJECT_DIR / "kbase/schema/address.yml",
            PROJECT_DIR / "ftrip/supplier/schema/supplier.yml",
        ],
    )
    # Example usage
    export_prisma_schema(
        schema,
        PROJECT_DIR / "tmp/ridge.prisma",
    )
