from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from sera.make.make_app import make_app
from sera.typing import Language

app = typer.Typer(pretty_exceptions_short=True, pretty_exceptions_enable=False)


@app.command()
def cli(
    app_dir: Annotated[
        Path,
        typer.Option("--app", help="Directory of the generated application"),
    ],
    schema_files: Annotated[
        list[Path],
        typer.Option(
            "-s", help="YAML schema files. Multiple files are merged automatically"
        ),
    ],
    api_collections: Annotated[
        list[str],
        typer.Option(
            "-c",
            "--collection",
            help="API collections to generate.",
        ),
    ] = [],
    language: Annotated[
        Language,
        typer.Option("-l", "--language", help="Language of the generated application"),
    ] = Language.Python,
    referenced_schema: Annotated[
        list[str],
        typer.Option(
            "-rs",
            "--referenced-schema",
            help="Classes in the schema that are defined in different modules, used as references and thus should not be generated.",
        ),
    ] = [],
):
    """Generate Python model classes from a schema file."""
    typer.echo(f"Generating application in {app_dir}")
    make_app(app_dir, schema_files, api_collections, language, referenced_schema)


if __name__ == "__main__":
    app()
