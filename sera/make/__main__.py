from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from sera.make.make_app import make_app

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
    ],
):
    """Generate Python model classes from a schema file."""
    typer.echo(f"Generating application in {app_dir}")
    make_app(app_dir, schema_files, api_collections)


app()
