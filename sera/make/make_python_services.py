from __future__ import annotations

from typing import Sequence

from codegen.models import DeferredVar, Program, expr, stmt
from loguru import logger

from sera.misc import assert_not_null
from sera.models import App, DataCollection, Package


def make_python_service_structure(app: App, collections: Sequence[DataCollection]):
    """Make the basic structure for the service."""
    app.services.ensure_exists()

    for collection in collections:
        make_python_service(collection, app.services)


def make_python_service(collection: DataCollection, target_pkg: Package):
    app = target_pkg.app

    outmod = target_pkg.module(collection.get_pymodule_name())
    if outmod.exists():
        logger.info("`{}` already exists. Skip generation.", outmod.path)
        return

    # assuming the collection has only one class
    cls = collection.cls
    id_type = assert_not_null(cls.get_id_property()).datatype.get_python_type().type

    program = Program()
    program.import_("__future__.annotations", True)
    program.import_(
        app.models.db.path + f".{collection.get_pymodule_name()}.{collection.name}",
        True,
    )
    program.import_(app.config.path + f".schema", True)
    program.import_("sera.libs.base_service.BaseAsyncService", True)

    program.root(
        stmt.LineBreak(),
        lambda ast00: ast00.class_(
            collection.get_service_name(),
            [expr.ExprIdent(f"BaseAsyncService[{id_type}, {cls.name}]")],
        )(
            lambda ast01: ast01.func(
                "__init__",
                [
                    DeferredVar.simple("self"),
                ],
            )(
                lambda ast02: ast02.expr(
                    expr.ExprFuncCall(
                        expr.ExprIdent("super().__init__"),
                        [
                            expr.ExprRawPython(f"schema.classes['{cls.name}']"),
                            expr.ExprIdent(cls.name),
                        ],
                    )
                ),
            ),
        ),
    )
    outmod.write(program)
