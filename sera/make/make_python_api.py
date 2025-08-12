from __future__ import annotations

from typing import Sequence

from codegen.models import DeferredVar, ImportHelper, PredefinedFn, Program, expr, stmt
from loguru import logger
from msgspec import convert

from sera.misc import assert_not_null, to_snake_case
from sera.models import App, DataCollection, Module, Package
from sera.typing import GLOBAL_IDENTS


def make_python_api(app: App, collections: Sequence[DataCollection]):
    """Make the basic structure for the API."""
    app.api.ensure_exists()
    app.api.pkg("routes").ensure_exists()

    # make routes
    routes: list[Module] = []
    for collection in collections:
        route = app.api.pkg("routes").pkg(collection.get_pymodule_name())

        controllers = []
        controllers.append(make_python_search_api(collection, route))
        controllers.append(make_python_get_by_id_api(collection, route))
        controllers.append(make_python_has_api(collection, route))
        controllers.append(make_python_create_api(collection, route))
        controllers.append(make_python_update_api(collection, route))

        routemod = route.module("route")
        if not routemod.exists():
            program = Program()
            program.import_("__future__.annotations", True)
            program.import_("litestar.Router", True)
            for get_route, get_route_fn in controllers:
                program.import_(get_route.path + "." + get_route_fn, True)

            program.root(
                stmt.LineBreak(),
                lambda ast: ast.assign(
                    DeferredVar.simple("router"),
                    expr.ExprFuncCall(
                        expr.ExprIdent("Router"),
                        [
                            PredefinedFn.keyword_assignment(
                                "path",
                                expr.ExprConstant(
                                    f"/api/{to_snake_case(collection.name).replace('_', '-')}"
                                ),
                            ),
                            PredefinedFn.keyword_assignment(
                                "route_handlers",
                                PredefinedFn.list(
                                    [
                                        expr.ExprIdent(get_route_fn)
                                        for get_route, get_route_fn in controllers
                                    ]
                                ),
                            ),
                            PredefinedFn.keyword_assignment(
                                "tags",
                                PredefinedFn.list(
                                    [expr.ExprConstant(collection.get_pymodule_name())]
                                ),
                            ),
                        ],
                    ),
                ),
            )

            routemod.write(program)
        routes.append(routemod)

    # make the main entry point
    make_main(app.api, routes)


def make_main(target_pkg: Package, routes: Sequence[Module]):
    outmod = target_pkg.module("app")
    if outmod.exists():
        logger.info("`{}` already exists. Skip generation.", outmod.path)
        return

    program = Program()
    program.import_("__future__.annotations", True)
    program.import_("litestar.Litestar", True)
    for route in routes:
        program.import_(route.path, False)

    program.root(
        stmt.LineBreak(),
        lambda ast: ast.assign(
            DeferredVar.simple("app_routes"),
            PredefinedFn.list(
                [expr.ExprIdent(route.path + ".router") for route in routes]
            ),
        ),
        lambda ast: ast.assign(
            DeferredVar.simple("app"),
            expr.ExprFuncCall(
                expr.ExprIdent("Litestar"),
                [
                    PredefinedFn.keyword_assignment(
                        "route_handlers",
                        expr.ExprIdent("app_routes"),
                    )
                ],
            ),
        ),
    )

    outmod.write(program)


def make_python_search_api(
    collection: DataCollection, target_pkg: Package
) -> tuple[Module, str]:
    """Make an endpoint for querying resources"""
    app = target_pkg.app

    program = Program()
    import_helper = ImportHelper(program, GLOBAL_IDENTS)

    program.import_("__future__.annotations", True)
    program.import_("litestar.post", True)
    program.import_(app.config.path + ".schema", True)
    program.import_(app.config.path + ".API_DEBUG", True)
    program.import_(
        app.services.path
        + f".{collection.get_pymodule_name()}.{collection.get_service_name()}",
        True,
    )
    program.import_(
        app.models.path + ".data_schema.dataschema",
        True,
    )
    program.import_("sera.libs.search_helper.Query", True)

    func_name = "search"

    program.root(
        stmt.LineBreak(),
        lambda ast: ast.assign(
            DeferredVar.simple("QUERYABLE_FIELDS"),
            PredefinedFn.set(
                [
                    expr.ExprConstant(propname)
                    for propname in collection.get_queryable_fields()
                ]
            ),
        ),
        stmt.LineBreak(),
        lambda ast: ast.assign(
            DeferredVar.simple("JOIN_QUERYABLE_FIELDS"),
            PredefinedFn.dict(
                [
                    (
                        expr.ExprConstant(propname),
                        PredefinedFn.set([expr.ExprConstant(f) for f in fields]),
                    )
                    for propname, fields in collection.get_join_queryable_fields().items()
                ]
            ),
        ),
        stmt.LineBreak(),
        stmt.PythonDecoratorStatement(
            expr.ExprFuncCall(
                expr.ExprIdent("post"),
                [
                    expr.ExprConstant("/q"),
                ],
            )
        ),
        lambda ast10: ast10.func(
            func_name,
            [
                DeferredVar.simple(
                    "data",
                    expr.ExprIdent("Query"),
                ),
                DeferredVar.simple(
                    "session",
                    import_helper.use("AsyncSession"),
                ),
            ],
            return_type=expr.ExprIdent(f"dict"),
            is_async=True,
        )(
            stmt.SingleExprStatement(
                expr.ExprConstant("Retrieving records matched a query")
            ),
            lambda ast100: ast100.assign(
                DeferredVar.simple("service"),
                expr.ExprFuncCall(
                    PredefinedFn.attr_getter(
                        expr.ExprIdent(collection.get_service_name()),
                        expr.ExprIdent("get_instance"),
                    ),
                    [],
                ),
            ),
            stmt.SingleExprStatement(
                expr.ExprFuncCall(
                    PredefinedFn.attr_getter(
                        expr.ExprIdent("data"),
                        expr.ExprIdent("validate_and_normalize"),
                    ),
                    [
                        PredefinedFn.item_getter(
                            PredefinedFn.attr_getter(
                                expr.ExprIdent("schema"), expr.ExprIdent("classes")
                            ),
                            expr.ExprConstant(collection.cls.name),
                        ),
                        expr.ExprIdent("QUERYABLE_FIELDS"),
                        expr.ExprIdent("JOIN_QUERYABLE_FIELDS"),
                        PredefinedFn.keyword_assignment(
                            "debug",
                            expr.ExprIdent("API_DEBUG"),
                        ),
                    ],
                )
            ),
            lambda ast102: ast102.assign(
                DeferredVar.simple("result"),
                expr.ExprAwait(
                    expr.ExprFuncCall(
                        PredefinedFn.attr_getter(
                            expr.ExprIdent("service"),
                            expr.ExprIdent("search"),
                        ),
                        [expr.ExprIdent("data"), expr.ExprIdent("session")],
                    )
                ),
            ),
            lambda ast103: ast103.return_(
                expr.ExprFuncCall(
                    PredefinedFn.attr_getter(
                        expr.ExprIdent("data"),
                        expr.ExprIdent("prepare_results"),
                    ),
                    [
                        PredefinedFn.item_getter(
                            PredefinedFn.attr_getter(
                                expr.ExprIdent("schema"), expr.ExprIdent("classes")
                            ),
                            expr.ExprConstant(collection.cls.name),
                        ),
                        expr.ExprIdent("dataschema"),
                        expr.ExprIdent("result"),
                    ],
                )
            ),
        ),
    )

    outmod = target_pkg.module("search")
    outmod.write(program)

    return outmod, func_name


def make_python_get_by_id_api(
    collection: DataCollection, target_pkg: Package
) -> tuple[Module, str]:
    """Make an endpoint for querying resource by id"""
    app = target_pkg.app

    program = Program()
    import_helper = ImportHelper(program, GLOBAL_IDENTS)

    program.import_("__future__.annotations", True)
    program.import_("litestar.get", True)
    program.import_("litestar.status_codes", True)
    program.import_("litestar.exceptions.HTTPException", True)
    program.import_(
        app.services.path
        + f".{collection.get_pymodule_name()}.{collection.get_service_name()}",
        True,
    )
    program.import_(
        app.models.data.path + f".{collection.get_pymodule_name()}.{collection.name}",
        True,
    )

    # assuming the collection has only one class
    cls = collection.cls
    id_type = assert_not_null(cls.get_id_property()).datatype.get_python_type().type

    func_name = "get_by_id"
    program.root(
        stmt.LineBreak(),
        stmt.PythonDecoratorStatement(
            expr.ExprFuncCall(
                expr.ExprIdent("get"),
                [
                    expr.ExprConstant("/{id:%s}" % id_type),
                ],
            )
        ),
        lambda ast10: ast10.func(
            func_name,
            [
                DeferredVar.simple(
                    "id",
                    expr.ExprIdent(id_type),
                ),
                DeferredVar.simple(
                    "session",
                    import_helper.use("AsyncSession"),
                ),
            ],
            return_type=expr.ExprIdent("dict"),
            is_async=True,
        )(
            stmt.SingleExprStatement(expr.ExprConstant("Retrieving record by id")),
            lambda ast100: ast100.assign(
                DeferredVar.simple("service"),
                expr.ExprFuncCall(
                    PredefinedFn.attr_getter(
                        expr.ExprIdent(collection.get_service_name()),
                        expr.ExprIdent("get_instance"),
                    ),
                    [],
                ),
            ),
            lambda ast11: ast11.assign(
                DeferredVar.simple("record"),
                expr.ExprAwait(
                    expr.ExprFuncCall(
                        expr.ExprIdent("service.get_by_id"),
                        [
                            expr.ExprIdent("id"),
                            expr.ExprIdent("session"),
                        ],
                    )
                ),
            ),
            lambda ast12: ast12.if_(PredefinedFn.is_null(expr.ExprIdent("record")))(
                lambda ast23: ast23.raise_exception(
                    expr.StandardExceptionExpr(
                        expr.ExprIdent("HTTPException"),
                        [
                            PredefinedFn.keyword_assignment(
                                "status_code",
                                expr.ExprIdent("status_codes.HTTP_404_NOT_FOUND"),
                            ),
                            PredefinedFn.keyword_assignment(
                                "detail",
                                expr.ExprIdent('f"Record with id {id} not found"'),
                            ),
                        ],
                    )
                )
            ),
            lambda ast13: ast13.return_(
                PredefinedFn.dict(
                    [
                        (
                            PredefinedFn.attr_getter(
                                expr.ExprIdent(cls.name), expr.ExprIdent("__name__")
                            ),
                            PredefinedFn.list(
                                [
                                    expr.ExprFuncCall(
                                        PredefinedFn.attr_getter(
                                            expr.ExprIdent(cls.name),
                                            expr.ExprIdent("from_db"),
                                        ),
                                        [expr.ExprIdent("record")],
                                    )
                                ]
                            ),
                        )
                    ]
                ),
            ),
        ),
    )

    outmod = target_pkg.module("get_by_id")
    outmod.write(program)

    return outmod, func_name


def make_python_has_api(
    collection: DataCollection, target_pkg: Package
) -> tuple[Module, str]:
    """Make an endpoint for querying resource by id"""
    app = target_pkg.app

    program = Program()
    import_helper = ImportHelper(program, GLOBAL_IDENTS)

    program.import_("__future__.annotations", True)
    program.import_("litestar.head", True)
    program.import_("litestar.status_codes", True)
    program.import_("litestar.exceptions.HTTPException", True)
    program.import_(
        app.services.path
        + f".{collection.get_pymodule_name()}.{collection.get_service_name()}",
        True,
    )

    # assuming the collection has only one class
    cls = collection.cls
    id_type = assert_not_null(cls.get_id_property()).datatype.get_python_type().type

    func_name = "has"
    program.root(
        stmt.LineBreak(),
        stmt.PythonDecoratorStatement(
            expr.ExprFuncCall(
                expr.ExprIdent("head"),
                [
                    expr.ExprConstant("/{id:%s}" % id_type),
                    PredefinedFn.keyword_assignment(
                        "status_code",
                        expr.ExprIdent("status_codes.HTTP_204_NO_CONTENT"),
                    ),
                ],
            )
        ),
        lambda ast10: ast10.func(
            func_name,
            [
                DeferredVar.simple(
                    "id",
                    expr.ExprIdent(id_type),
                ),
                DeferredVar.simple(
                    "session",
                    import_helper.use("AsyncSession"),
                ),
            ],
            return_type=expr.ExprConstant(None),
            is_async=True,
        )(
            stmt.SingleExprStatement(
                expr.ExprConstant("Checking if record exists by id")
            ),
            lambda ast100: ast100.assign(
                DeferredVar.simple("service"),
                expr.ExprFuncCall(
                    PredefinedFn.attr_getter(
                        expr.ExprIdent(collection.get_service_name()),
                        expr.ExprIdent("get_instance"),
                    ),
                    [],
                ),
            ),
            lambda ast11: ast11.assign(
                DeferredVar.simple("record_exist"),
                expr.ExprAwait(
                    expr.ExprFuncCall(
                        expr.ExprIdent("service.has_id"),
                        [
                            expr.ExprIdent("id"),
                            expr.ExprIdent("session"),
                        ],
                    )
                ),
            ),
            lambda ast12: ast12.if_(expr.ExprNegation(expr.ExprIdent("record_exist")))(
                lambda ast23: ast23.raise_exception(
                    expr.StandardExceptionExpr(
                        expr.ExprIdent("HTTPException"),
                        [
                            PredefinedFn.keyword_assignment(
                                "status_code",
                                expr.ExprIdent("status_codes.HTTP_404_NOT_FOUND"),
                            ),
                            PredefinedFn.keyword_assignment(
                                "detail",
                                expr.ExprIdent('f"Record with id {id} not found"'),
                            ),
                        ],
                    )
                )
            ),
            lambda ast13: ast13.return_(expr.ExprConstant(None)),
        ),
    )

    outmod = target_pkg.module("has")
    outmod.write(program)

    return outmod, func_name


def make_python_create_api(collection: DataCollection, target_pkg: Package):
    """Make an endpoint for creating a resource"""
    app = target_pkg.app

    program = Program()
    import_helper = ImportHelper(program, GLOBAL_IDENTS)

    program.import_("__future__.annotations", True)
    program.import_("litestar.post", True)
    program.import_(
        app.services.path
        + f".{collection.get_pymodule_name()}.{collection.get_service_name()}",
        True,
    )
    program.import_(
        app.models.data.path
        + f".{collection.get_pymodule_name()}.Create{collection.name}",
        True,
    )

    # assuming the collection has only one class
    cls = collection.cls
    is_on_create_update_props = any(
        prop.data.system_controlled is not None
        and prop.data.system_controlled.is_on_create_value_updated()
        for prop in cls.properties.values()
    )
    idprop = assert_not_null(cls.get_id_property())

    if is_on_create_update_props:
        program.import_("sera.libs.api_helper.SingleAutoUSCP", True)

    func_name = "create"

    program.root(
        stmt.LineBreak(),
        stmt.PythonDecoratorStatement(
            expr.ExprFuncCall(
                expr.ExprIdent("post"),
                [
                    expr.ExprConstant("/"),
                ]
                + (
                    [
                        PredefinedFn.keyword_assignment(
                            "dto",
                            PredefinedFn.item_getter(
                                expr.ExprIdent("SingleAutoUSCP"),
                                expr.ExprIdent(f"Create{cls.name}"),
                            ),
                        )
                    ]
                    if is_on_create_update_props
                    else []
                ),
            )
        ),
        lambda ast10: ast10.func(
            func_name,
            [
                DeferredVar.simple(
                    "data",
                    expr.ExprIdent(f"Create{cls.name}"),
                ),
                DeferredVar.simple(
                    "session",
                    import_helper.use("AsyncSession"),
                ),
            ],
            return_type=expr.ExprIdent(idprop.datatype.get_python_type().type),
            is_async=True,
        )(
            stmt.SingleExprStatement(expr.ExprConstant("Creating new record")),
            lambda ast100: ast100.assign(
                DeferredVar.simple("service"),
                expr.ExprFuncCall(
                    PredefinedFn.attr_getter(
                        expr.ExprIdent(collection.get_service_name()),
                        expr.ExprIdent("get_instance"),
                    ),
                    [],
                ),
            ),
            lambda ast13: ast13.return_(
                PredefinedFn.attr_getter(
                    expr.ExprAwait(
                        expr.ExprMethodCall(
                            expr.ExprIdent("service"),
                            "create",
                            [
                                expr.ExprMethodCall(
                                    expr.ExprIdent("data"), "to_db", []
                                ),
                                expr.ExprIdent("session"),
                            ],
                        )
                    ),
                    expr.ExprIdent(idprop.name),
                )
            ),
        ),
    )

    outmod = target_pkg.module("create")
    outmod.write(program)

    return outmod, func_name


def make_python_update_api(collection: DataCollection, target_pkg: Package):
    """Make an endpoint for updating resource"""
    app = target_pkg.app

    program = Program()
    import_helper = ImportHelper(program, GLOBAL_IDENTS)

    program.import_("__future__.annotations", True)
    program.import_("litestar.put", True)
    program.import_(
        app.services.path
        + f".{collection.get_pymodule_name()}.{collection.get_service_name()}",
        True,
    )
    program.import_(
        app.models.data.path
        + f".{collection.get_pymodule_name()}.Update{collection.name}",
        True,
    )

    # assuming the collection has only one class
    cls = collection.cls
    id_prop = assert_not_null(cls.get_id_property())
    id_type = id_prop.datatype.get_python_type().type

    is_on_update_update_props = any(
        prop.data.system_controlled is not None
        and prop.data.system_controlled.is_on_update_value_updated()
        for prop in cls.properties.values()
    )
    if is_on_update_update_props:
        program.import_("sera.libs.api_helper.SingleAutoUSCP", True)

    func_name = "update"

    program.root(
        stmt.LineBreak(),
        stmt.PythonDecoratorStatement(
            expr.ExprFuncCall(
                expr.ExprIdent("put"),
                [
                    expr.ExprConstant("/{id:%s}" % id_type),
                ]
                + (
                    [
                        PredefinedFn.keyword_assignment(
                            "dto",
                            PredefinedFn.item_getter(
                                expr.ExprIdent("SingleAutoUSCP"),
                                expr.ExprIdent(f"Update{cls.name}"),
                            ),
                        )
                    ]
                    if is_on_update_update_props
                    else []
                ),
            )
        ),
        lambda ast10: ast10.func(
            func_name,
            [
                DeferredVar.simple(
                    "id",
                    expr.ExprIdent(id_type),
                ),
                DeferredVar.simple(
                    "data",
                    expr.ExprIdent(f"Update{cls.name}"),
                ),
                DeferredVar.simple(
                    "session",
                    import_helper.use("AsyncSession"),
                ),
            ],
            return_type=expr.ExprIdent(id_prop.datatype.get_python_type().type),
            is_async=True,
        )(
            stmt.SingleExprStatement(expr.ExprConstant("Update an existing record")),
            lambda ast100: ast100.assign(
                DeferredVar.simple("service"),
                expr.ExprFuncCall(
                    PredefinedFn.attr_getter(
                        expr.ExprIdent(collection.get_service_name()),
                        expr.ExprIdent("get_instance"),
                    ),
                    [],
                ),
            ),
            stmt.SingleExprStatement(
                PredefinedFn.attr_setter(
                    expr.ExprIdent("data"),
                    expr.ExprIdent(id_prop.name),
                    expr.ExprIdent("id"),
                )
            ),
            lambda ast13: ast13.return_(
                PredefinedFn.attr_getter(
                    expr.ExprAwait(
                        expr.ExprMethodCall(
                            expr.ExprIdent("service"),
                            "update",
                            [
                                expr.ExprMethodCall(
                                    expr.ExprIdent("data"), "to_db", []
                                ),
                                expr.ExprIdent("session"),
                            ],
                        )
                    ),
                    expr.ExprIdent(id_prop.name),
                )
            ),
        ),
    )

    outmod = target_pkg.module("update")
    outmod.write(program)

    return outmod, func_name
