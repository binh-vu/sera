from pathlib import Path
from typing import Annotated

import typer

from sera.models import Cardinality, Class, DataProperty, Schema, parse_schema
from sera.models._datatype import DataType


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
        lines.append(
            f"  {'id'.ljust(30)} {'Int'.ljust(10)} @id @default(autoincrement())"
        )
    #     lines.append(f"  @@unique([%s])" % ", ".join(cls.properties.keys()))

    for prop in cls.properties.values():
        propattrs = ""
        if isinstance(prop, DataProperty):
            proptype = get_prisma_field_type(prop.datatype)
            if prop.is_optional:
                proptype = f"{proptype}?"
            if prop.db is not None and prop.db.is_primary_key:
                propattrs += "@id "

            lines.append(f"  {prop.name.ljust(30)} {proptype.ljust(10)} {propattrs}")
            continue

        if prop.cardinality == Cardinality.MANY_TO_MANY:
            # For many-to-many relationships, we need to handle the join table
            lines.append(
                f"  {prop.name.ljust(30)} {(prop.target.name + '[]').ljust(10)}"
            )
        else:
            lines.append(
                f"  {(prop.name + '_').ljust(30)} {prop.target.name.ljust(10)} @relation(fields: [{prop.name}], references: [id])"
            )
            lines.append(f"  {prop.name.ljust(30)} {'Int'.ljust(10)} @unique")

    lines.append("")
    for upstream_cls, reverse_upstream_prop in schema.get_upstream_classes(cls):
        if (
            reverse_upstream_prop.cardinality == Cardinality.MANY_TO_ONE
            or reverse_upstream_prop.cardinality == Cardinality.MANY_TO_MANY
        ):

            proptype = f"{upstream_cls.name}[]"
        else:
            proptype = upstream_cls.name + "?"
        lines.append(f"  {upstream_cls.name.lower().ljust(30)} {proptype.ljust(10)}")

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


app = typer.Typer(pretty_exceptions_short=True, pretty_exceptions_enable=False)


@app.command()
def cli(
    schema_files: Annotated[
        list[Path],
        typer.Option(
            "-s", help="YAML schema files. Multiple files are merged automatically"
        ),
    ],
    outfile: Annotated[
        Path,
        typer.Option(
            "-o", "--output", help="Output file for the Prisma schema", writable=True
        ),
    ],
):
    schema = parse_schema(
        "sera",
        schema_files,
    )
    export_prisma_schema(
        schema,
        outfile,
    )


if __name__ == "__main__":
    app()
