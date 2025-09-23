from __future__ import annotations

from codegen.models import PredefinedFn, Program, expr, stmt
from codegen.models.var import DeferredVar
from loguru import logger

from sera.make.ts_frontend.make_class_schema import make_class_schema
from sera.make.ts_frontend.make_draft_model import make_draft
from sera.make.ts_frontend.make_query import make_query
from sera.misc import assert_isinstance, assert_not_null, to_camel_case, to_snake_case
from sera.models import (
    Class,
    DataProperty,
    Enum,
    ObjectProperty,
    Package,
    Schema,
    TsTypeWithDep,
)


def make_typescript_data_model(schema: Schema, target_pkg: Package):
    """Generate TypeScript data model from the schema. The data model aligns with the public data model in Python, not the database model."""
    app = target_pkg.app

    # mapping from type alias of idprop to its real type
    idprop_aliases = {}
    for cls in schema.classes.values():
        idprop = cls.get_id_property()
        if idprop is not None:
            idprop_aliases[f"{cls.name}Id"] = (
                idprop.get_data_model_datatype().get_typescript_type()
            )

    def get_normal_deser_args(
        prop: DataProperty | ObjectProperty,
    ) -> expr.Expr:
        """Extract the value from the data record from the server response to set to the class property in the client."""
        handle_optional = lambda value: expr.ExprTernary(
            expr.ExprNotEqual(value, expr.ExprConstant(None)),
            value,
            expr.ExprConstant("undefined"),
        )

        if isinstance(prop, DataProperty):
            value = PredefinedFn.attr_getter(
                expr.ExprIdent("data"), expr.ExprIdent(prop.name)
            )
            if prop.is_optional:
                value = handle_optional(value)
                value.true_expr = (
                    prop.datatype.get_typescript_type().get_json_deser_func(
                        value.true_expr
                    )
                )
            else:
                value = prop.datatype.get_typescript_type().get_json_deser_func(value)

            return value

        assert isinstance(prop, ObjectProperty)
        if prop.target.db is not None:
            value = PredefinedFn.attr_getter(
                expr.ExprIdent("data"), expr.ExprIdent(prop.name + "_id")
            )
            if prop.is_optional:
                value = handle_optional(value)
            return value
        else:
            if prop.cardinality.is_star_to_many():
                # optional type for a list is simply an empty list, we don't need to check for None
                value = PredefinedFn.map_list(
                    PredefinedFn.attr_getter(
                        expr.ExprIdent("data"),
                        expr.ExprIdent(prop.name),
                    ),
                    lambda item: expr.ExprMethodCall(
                        expr.ExprIdent(
                            assert_isinstance(prop, ObjectProperty).target.name
                        ),
                        "deser",
                        [item],
                    ),
                )
                return value
            else:
                value = expr.ExprFuncCall(
                    PredefinedFn.attr_getter(
                        expr.ExprIdent(prop.target.name),
                        expr.ExprIdent("deser"),
                    ),
                    [
                        PredefinedFn.attr_getter(
                            expr.ExprIdent("data"),
                            expr.ExprIdent(prop.name),
                        )
                    ],
                )
                if prop.is_optional:
                    value = handle_optional(value)
                return value

    def make_normal(cls: Class, pkg: Package):
        """Make a data model for the normal Python data model"""
        if not cls.is_public:
            # skip classes that are not public
            return

        idprop = cls.get_id_property()
        program = Program()
        program.import_(
            f"@.models.{pkg.dir.name}.Draft{cls.name}.Draft{cls.name}", True
        )

        prop_defs = []
        prop_constructor_assigns = []
        deser_args = []

        for prop in cls.properties.values():
            if prop.data.is_private:
                # skip private fields as this is for APIs exchange
                continue

            propname = to_camel_case(prop.name)

            if isinstance(prop, DataProperty):
                tstype = prop.get_data_model_datatype().get_typescript_type()
                for dep in tstype.deps:
                    program.import_(dep, True)

                if idprop is not None and prop.name == idprop.name:
                    # use id type alias
                    tstype = TsTypeWithDep(
                        type=f"{cls.name}Id", spectype=tstype.spectype
                    )

                if prop.is_optional:
                    # convert type to optional
                    tstype = tstype.as_optional_type()

                deser_args.append(
                    (
                        expr.ExprIdent(propname),
                        get_normal_deser_args(prop),
                    )
                )
            else:
                assert isinstance(prop, ObjectProperty)
                if prop.target.db is not None:
                    # this class is stored in the database, we store the id instead
                    propname = propname + "Id"
                    tstype = TsTypeWithDep(
                        type=f"{prop.target.name}Id",
                        spectype=assert_not_null(prop.target.get_id_property())
                        .get_data_model_datatype()
                        .get_typescript_type()
                        .spectype,
                        deps=(
                            [
                                f"@.models.{prop.target.get_tsmodule_name()}.{prop.target.name}.{prop.target.name}Id"
                            ]
                            if prop.target.name != cls.name
                            else []
                        ),
                    )
                    if prop.cardinality.is_star_to_many():
                        tstype = tstype.as_list_type()
                    elif prop.is_optional:
                        # convert type to optional only if it isn't a list
                        tstype = tstype.as_optional_type()
                    deser_args.append(
                        (
                            expr.ExprIdent(propname),
                            get_normal_deser_args(prop),
                        )
                    )
                else:
                    # we are going to store the whole object
                    tstype = TsTypeWithDep(
                        type=prop.target.name,
                        spectype=prop.target.name,
                        deps=[
                            f"@.models.{prop.target.get_tsmodule_name()}.{prop.target.name}.{prop.target.name}"
                        ],
                    )
                    if prop.cardinality.is_star_to_many():
                        tstype = tstype.as_list_type()
                        deser_args.append(
                            (
                                expr.ExprIdent(propname),
                                get_normal_deser_args(prop),
                            )
                        )
                    else:
                        if prop.is_optional:
                            # convert type to optional only if it isn't a list
                            tstype = tstype.as_optional_type()
                        deser_args.append(
                            (
                                expr.ExprIdent(propname),
                                get_normal_deser_args(prop),
                            )
                        )

                for dep in tstype.deps:
                    program.import_(
                        dep,
                        True,
                    )

            prop_defs.append(stmt.DefClassVarStatement(propname, tstype.type))
            prop_constructor_assigns.append(
                stmt.AssignStatement(
                    PredefinedFn.attr_getter(
                        expr.ExprIdent("this"),
                        expr.ExprIdent(propname),
                    ),
                    expr.ExprIdent("args." + propname),
                )
            )

        program.root(
            stmt.LineBreak(),
            (
                stmt.TypescriptStatement(
                    f"export type {cls.name}Id = {idprop.get_data_model_datatype().get_typescript_type().type};"
                )
                if idprop is not None
                else None
            ),
            stmt.LineBreak(),
            lambda ast00: ast00.class_like(
                "interface",
                cls.name + "ConstructorArgs",
            )(*prop_defs),
            stmt.LineBreak(),
            lambda ast10: ast10.class_(cls.name)(
                *prop_defs,
                stmt.LineBreak(),
                lambda ast11: ast11.func(
                    "constructor",
                    [
                        DeferredVar.simple(
                            "args", expr.ExprIdent(cls.name + "ConstructorArgs")
                        ),
                    ],
                )(*prop_constructor_assigns),
                stmt.LineBreak(),
                lambda ast12: ast12.func(
                    "className",
                    [],
                    expr.ExprIdent("string"),
                    is_static=True,
                    modifiers=["get"],
                    comment="Name of the class in the Schema",
                )(
                    stmt.ReturnStatement(expr.ExprConstant(cls.name)),
                ),
                stmt.LineBreak(),
                lambda ast12: ast12.func(
                    "deser",
                    [
                        DeferredVar.simple("data", expr.ExprIdent("any")),
                    ],
                    expr.ExprIdent(cls.name),
                    is_static=True,
                    comment="Deserialize the data from the server to create a new instance of the class",
                )(
                    lambda ast: ast.return_(
                        expr.ExprNewInstance(
                            expr.ExprIdent(cls.name), [PredefinedFn.dict(deser_args)]
                        )
                    )
                ),
                stmt.LineBreak(),
                lambda ast13: ast13.func(
                    "toDraft",
                    [],
                    expr.ExprIdent(f"Draft{cls.name}"),
                    comment="Convert the class instance to a draft for editing",
                )(
                    stmt.ReturnStatement(
                        expr.ExprMethodCall(
                            expr.ExprIdent(f"Draft{cls.name}"),
                            "update",
                            [expr.ExprIdent("this")],
                        )
                    ),
                ),
            ),
        )

        pkg.module(cls.name).write(program)

    def make_table(cls: Class, pkg: Package):
        if not cls.is_public or cls.db is None:
            # skip classes that are not public and not stored in the database
            return

        outmod = pkg.module(cls.name + "Table")
        if outmod.exists():
            # skip if the module already exists
            logger.info(f"Module {outmod.path} already exists, skip")
            return

        program = Program()
        program.import_(f"@.models.{pkg.dir.name}.{cls.name}.{cls.name}", True)
        program.import_(f"@.models.{pkg.dir.name}.{cls.name}.{cls.name}Id", True)
        program.import_(f"@.models.{pkg.dir.name}.{cls.name}Query.query", True)
        program.import_(
            f"@.models.{pkg.dir.name}.Draft{cls.name}.Draft{cls.name}", True
        )
        program.import_("sera-db.Table", True)
        program.import_("sera-db.DB", True)

        program.root(
            stmt.LineBreak(),
            lambda ast00: ast00.class_(
                f"{cls.name}Table",
                [expr.ExprIdent(f"Table<{cls.name}Id, {cls.name}, Draft{cls.name}>")],
            )(
                lambda ast01: ast01.func(
                    "constructor",
                    [
                        DeferredVar.simple(
                            "db",
                            expr.ExprIdent("DB"),
                        )
                    ],
                )(
                    stmt.SingleExprStatement(
                        expr.ExprFuncCall(
                            expr.ExprIdent("super"),
                            [
                                PredefinedFn.dict(
                                    [
                                        (
                                            expr.ExprIdent("cls"),
                                            expr.ExprIdent(cls.name),
                                        ),
                                        (
                                            expr.ExprIdent("remoteURL"),
                                            expr.ExprConstant(
                                                f"/api/{to_snake_case(cls.name).replace('_', '-')}"
                                            ),
                                        ),
                                        (
                                            expr.ExprIdent("db"),
                                            expr.ExprIdent("db"),
                                        ),
                                        (
                                            expr.ExprIdent("queryProcessor"),
                                            expr.ExprIdent("query"),
                                        ),
                                    ]
                                )
                            ],
                        )
                    )
                ),
            ),
        )

        outmod.write(program)

    def make_index(pkg: Package):
        outmod = pkg.module("index")
        if outmod.exists():
            # skip if the module already exists
            logger.info(f"Module {outmod.path} already exists, skip")
            return

        export_types = []
        export_iso_types = []  # isolatedModules required separate export type clause

        program = Program()
        program.import_(f"@.models.{pkg.dir.name}.{cls.name}.{cls.name}", True)
        export_types.append(cls.name)
        if cls.db is not None:
            # only import the id if this class is stored in the database
            program.import_(f"@.models.{pkg.dir.name}.{cls.name}.{cls.name}Id", True)
            export_iso_types.append(f"{cls.name}Id")

        program.import_(
            f"@.models.{pkg.dir.name}.{cls.name}Schema.{cls.name}Schema", True
        )
        program.import_(
            f"@.models.{pkg.dir.name}.{cls.name}Query.{cls.name}Query", True
        )
        export_types.append(f"{cls.name}Schema")
        export_iso_types.append(f"{cls.name}Query")
        program.import_(
            f"@.models.{pkg.dir.name}.{cls.name}Schema.{cls.name}SchemaType", True
        )
        export_iso_types.append(f"{cls.name}SchemaType")

        program.import_(
            f"@.models.{pkg.dir.name}.Draft{cls.name}.Draft{cls.name}", True
        )
        export_types.append(f"Draft{cls.name}")
        if cls.db is not None:
            program.import_(
                f"@.models.{pkg.dir.name}.{cls.name}Table.{cls.name}Table", True
            )
            export_types.append(f"{cls.name}Table")

        program.root(
            stmt.LineBreak(),
            stmt.TypescriptStatement("export { %s };" % (", ".join(export_types))),
            (
                stmt.TypescriptStatement(
                    "export type { %s };" % (", ".join(export_iso_types))
                )
            ),
        )

        outmod.write(program)

    for cls in schema.topological_sort():
        pkg = target_pkg.pkg(cls.get_tsmodule_name())
        make_normal(cls, pkg)
        make_draft(schema, cls, pkg, idprop_aliases)
        make_query(schema, cls, pkg)
        make_table(cls, pkg)
        make_class_schema(schema, cls, pkg)

        make_index(pkg)


def make_typescript_enum(schema: Schema, target_pkg: Package):
    """Make typescript enum for the schema"""
    enum_pkg = target_pkg.pkg("enums")

    def make_enum(enum: Enum, pkg: Package):
        program = Program()
        program.root(
            stmt.LineBreak(),
            lambda ast: ast.class_like("enum", enum.name)(
                *[
                    stmt.DefEnumValueStatement(
                        name=value.name,
                        value=expr.ExprConstant(value.value),
                    )
                    for value in enum.values.values()
                ]
            ),
        )
        pkg.module(enum.get_tsmodule_name()).write(program)

    for enum in schema.enums.values():
        make_enum(enum, enum_pkg)

    program = Program()
    for enum in schema.enums.values():
        program.import_(f"@.models.enums.{enum.get_tsmodule_name()}.{enum.name}", True)

    program.root(
        stmt.LineBreak(),
        stmt.TypescriptStatement(
            "export { "
            + ", ".join([enum.name for enum in schema.enums.values()])
            + "};"
        ),
    )
    enum_pkg.module("index").write(program)
