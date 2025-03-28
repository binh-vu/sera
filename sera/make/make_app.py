from __future__ import annotations

import os
from pathlib import Path
from pydoc import doc
from typing import Annotated

from codegen.models import DeferredVar, PredefinedFn, Program, expr, stmt
from loguru import logger
from sera.make.make_python_api import make_python_api
from sera.make.make_python_model import (
    make_python_data_model,
    make_python_relational_model,
)
from sera.make.make_python_services import make_python_service_structure
from sera.models import App, DataCollection, Language, parse_schema


def make_config(app: App):
    """Make the configuration for the application."""
    if app.config.exists():
        logger.info("`{}` already exists. Skip generation.", app.config.path)
        return

    program = Program()
    program.import_("__future__.annotations", True)
    program.import_("os", False)
    program.import_("serde.yaml", False)
    program.import_("pathlib.Path", True)
    program.import_("sera.models.parse_schema", True)

    program.root(
        lambda ast: ast.if_(
            PredefinedFn.not_has_item(
                expr.ExprIdent("os.environ"), expr.ExprConstant("CFG_FILE")
            )
        )(
            lambda ast01: ast01.assign(
                DeferredVar.simple("CFG_FILE"),
                expr.ExprRawPython("Path(__file__).parent.parent / 'config.yml'"),
            ),
        ),
        lambda ast: ast.else_()(
            lambda ast01: ast01.assign(
                DeferredVar.simple("CFG_FILE"),
                expr.ExprRawPython('Path(os.environ["CFG_FILE"])'),
            ),
        ),
        lambda ast: ast.assign(
            DeferredVar.simple("cfg"),
            expr.ExprFuncCall(
                expr.ExprIdent("serde.yaml.deser"), [expr.ExprIdent("CFG_FILE")]
            ),
        ),
        stmt.LineBreak(),
        lambda ast: ast.assign(
            DeferredVar.simple("DB_CONNECTION"),
            expr.ExprIdent("cfg['db']['connection']"),
        ),
        lambda ast: ast.assign(
            DeferredVar.simple("DB_DEBUG"),
            expr.ExprIdent('os.environ.get("DB_DEBUG", "0") == "1"'),
        ),
        lambda ast: ast.assign(
            DeferredVar.simple("ROUTER_DEBUG"),
            expr.ExprIdent('os.environ.get("ROUTER_DEBUG", "0") == "1"'),
        ),
        stmt.LineBreak(),
        lambda ast: ast.assign(
            DeferredVar.simple("PKG_DIR"),
            expr.ExprRawPython("Path(__file__).parent"),
        ),
        lambda ast: ast.assign(
            DeferredVar.simple("schema"),
            expr.ExprFuncCall(
                expr.ExprIdent("parse_schema"),
                [
                    PredefinedFn.list(
                        [
                            expr.ExprDivision(
                                expr.ExprIdent("PKG_DIR"),
                                expr.ExprConstant(
                                    os.path.relpath(path.absolute(), app.root.dir)
                                ),
                            )
                            for path in app.schema_files
                        ]
                    )
                ],
            ),
        ),
    )

    app.config.write(program)


def make_app(
    app_dir: Annotated[
        Path,
        doc("Directory of the generated application"),
    ],
    schema_files: Annotated[
        list[Path],
        doc("YAML schema files. Multiple files are merged automatically"),
    ],
    api_collections: Annotated[
        list[str],
        doc("API collections to generate."),
    ],
    language: Annotated[
        Language,
        doc(
            "Language of the generated application. Currently only Python is supported."
        ),
    ] = Language.Python,
):
    schema = parse_schema(schema_files)

    app = App(app_dir.name, app_dir, schema_files, language)

    # generate application configuration
    make_config(app)

    # generate models from schema
    make_python_data_model(schema, app.models.pkg("data"))
    make_python_relational_model(schema, app.models.pkg("db"), app.models.pkg("data"))

    collections = [DataCollection(schema.classes[cname]) for cname in api_collections]

    # generate API
    make_python_api(app, collections)

    # generate services
    make_python_service_structure(app, collections)

    return app


if __name__ == "__main__":
    make_app(
        Path("/Volumes/research/workspace/libs/sera/tests/resources/myapp"),
        [
            Path(
                "/Volumes/research/workspace/libs/sera/tests/resources/schema/product.yml"
            )
        ],
        ["Product", "Category"],
    )
