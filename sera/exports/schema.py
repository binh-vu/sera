from pathlib import Path
from typing import Annotated

import orjson
import typer

from sera.misc import assert_not_null, to_snake_case
from sera.models import Cardinality, DataProperty, Schema, parse_schema


def export_tbls(schema: Schema, outfile: Path):
    out = {
        "name": schema.name,
        "tables": [],
        "relations": [],
    }

    DUMMY_IDPROP = "dkey"

    for cls in schema.topological_sort():
        table = {
            "name": cls.name,
            "type": "BASE TABLE",
            "columns": [],
            "constraints": [],
        }

        if cls.db is None:
            # This class has no database mapping, we must generate a default key for it
            table["columns"].append(
                {
                    "name": DUMMY_IDPROP,
                    "type": "UNSET",
                    "nullable": False,
                }
            )

        for prop in cls.properties.values():
            column = {
                "name": prop.name,
                "nullable": not prop.is_optional,
            }

            if isinstance(prop, DataProperty):
                column["type"] = prop.datatype.get_python_type().type
                if prop.db is not None and prop.db.is_primary_key:
                    table["constraints"].append(
                        {
                            "name": f"{cls.name}_pkey",
                            "type": "PRIMARY KEY",
                            "def": f"PRIMARY KEY ({prop.name})",
                            "table": cls.name,
                            "referenced_table": cls.name,
                            "columns": [prop.name],
                        }
                    )

                    if prop.db.foreign_key is not None:
                        idprop = assert_not_null(prop.db.foreign_key.get_id_property())
                        out["relations"].append(
                            {
                                "table": cls.name,
                                "columns": [prop.name],
                                "cardinality": "zero_or_one",
                                "parent_table": prop.db.foreign_key.name,
                                "parent_columns": [idprop_name],
                                "parent_cardinality": "zero_or_one",
                                "def": f"FOREIGN KEY ({prop.name}) REFERENCES {prop.db.foreign_key.name}({idprop_name})",
                            }
                        )
            else:
                if prop.cardinality == Cardinality.MANY_TO_MANY:
                    # For many-to-many relationships, we need to create a join table
                    jointable = {
                        "name": f"{cls.name}{prop.target.name}",
                        "type": "JOIN TABLE",
                        "columns": [
                            {
                                "name": f"{to_snake_case(cls.name)}_id",
                                "type": assert_not_null(cls.get_id_property())
                                .datatype.get_python_type()
                                .type,
                                "nullable": False,
                            },
                            {
                                "name": f"{to_snake_case(prop.target.name)}_id",
                                "type": assert_not_null(prop.target.get_id_property())
                                .datatype.get_python_type()
                                .type,
                                "nullable": False,
                            },
                        ],
                    }
                    out["tables"].append(jointable)
                    out["relations"].extend(
                        [
                            {
                                "table": f"{cls.name}{prop.target.name}",
                                "columns": [f"{to_snake_case(cls.name)}_id"],
                                "cardinality": "zero_or_more",
                                "parent_table": cls.name,
                                "parent_columns": [
                                    assert_not_null(cls.get_id_property()).name
                                ],
                                "parent_cardinality": "zero_or_one",
                                "def": "",  # LiamERD does not use `def` so we can leave it empty for now
                            },
                            {
                                "table": f"{cls.name}{prop.target.name}",
                                "columns": [f"{to_snake_case(prop.target.name)}_id"],
                                "cardinality": "zero_or_more",
                                "parent_table": prop.target.name,
                                "parent_columns": [
                                    assert_not_null(prop.target.get_id_property()).name
                                ],
                                "parent_cardinality": "zero_or_one",
                                "def": "",
                            },
                        ]
                    )
                    # we actually want to skip adding this N-to-N column
                    continue

                if prop.target.db is not None:
                    idprop = assert_not_null(prop.target.get_id_property())
                    idprop_name = idprop.name
                    column["type"] = idprop.datatype.get_python_type().type
                else:
                    column["type"] = prop.target.name
                    idprop_name = (
                        DUMMY_IDPROP  # a dummy property name for visualization purposes
                    )
                    assert idprop_name not in prop.target.properties

                # somehow LiamERD only support zero_or_more or zero_or_one (exactly one does not work)
                if prop.cardinality == Cardinality.ONE_TO_ONE:
                    cardinality = "zero_or_one"
                    parent_cardinality = "zero_or_one"
                elif prop.cardinality == Cardinality.ONE_TO_MANY:
                    cardinality = "zero_or_one"
                    parent_cardinality = "zero_or_more"
                elif prop.cardinality == Cardinality.MANY_TO_ONE:
                    cardinality = "zero_or_more"
                    parent_cardinality = "zero_or_one"
                elif prop.cardinality == Cardinality.MANY_TO_MANY:
                    raise Exception("Unreachable")

                out["relations"].append(
                    {
                        "table": cls.name,
                        "columns": [prop.name],
                        "cardinality": cardinality,
                        "parent_table": prop.target.name,
                        "parent_columns": [idprop_name],
                        "parent_cardinality": parent_cardinality,
                        "def": f"FOREIGN KEY ({prop.name}) REFERENCES {prop.target.name}({idprop_name})",
                    }
                )

            table["columns"].append(column)

        out["tables"].append(table)

    outfile.parent.mkdir(parents=True, exist_ok=True)
    outfile.write_bytes(orjson.dumps(out, option=orjson.OPT_INDENT_2))


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
            "-o", "--output", help="Output file for the tbls schema", writable=True
        ),
    ],
):
    schema = parse_schema(
        "sera",
        schema_files,
    )
    export_tbls(
        schema,
        outfile,
    )


if __name__ == "__main__":
    app()
