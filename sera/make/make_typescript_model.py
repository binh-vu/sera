from __future__ import annotations

from operator import is_
from typing import Any, Callable

from codegen.models import AST, PredefinedFn, Program, expr, stmt
from codegen.models.var import DeferredVar
from sera.misc import to_camel_case, to_pascal_case
from sera.models import Class, DataProperty, Package, Schema


def make_typescript_data_model(schema: Schema, target_pkg: Package):
    """Generate TypeScript data model from the schema. The data model aligns with the public data model in Python, not the database model."""
    app = target_pkg.app

    def make_normal(cls: Class, pkg: Package):
        """Make a data model for the normal Python data model"""
        if not cls.is_public:
            # skip classes that are not public
            return

        program = Program()

        prop_defs = []
        prop_constructor_assigns = []
        deser_args = []

        for prop in cls.properties.values():
            if prop.is_private:
                # skip private fields as this is for APIs exchange
                continue

            if isinstance(prop, DataProperty):
                tstype = prop.datatype.get_typescript_type()
                if tstype.dep is not None:
                    program.import_(tstype.dep, True)

                propname = to_camel_case(prop.name)
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
                deser_args.append(
                    (
                        expr.ExprIdent(propname),
                        PredefinedFn.attr_getter(
                            expr.ExprIdent("data"), expr.ExprIdent(prop.name)
                        ),
                    )
                )

        program.root(
            lambda ast00: ast00.interface(
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
            ),
        )

        pkg.module(cls.name).write(program)

    def make_draft(cls: Class, pkg: Package):
        if not cls.is_public:
            # skip classes that are not public
            return

        draft_clsname = "Draft" + cls.name

        program = Program()
        program.import_(f"@.models.{pkg.dir.name}.{cls.name}.{cls.name}", True)
        program.import_("mobx.makeObservable", True)
        program.import_("mobx.observable", True)
        program.import_("mobx.action", True)

        program.root.linebreak()

        # make sure that the property stale is not in existing properties
        if "stale" in cls.properties:
            raise ValueError(f"Class {cls.name} already has property stale")

        # information about class primary key
        cls_pk = None
        observable_args: list[tuple[expr.Expr, expr.ExprIdent]] = []
        prop_defs = []
        prop_constructor_assigns = []
        # attrs needed for the cls.create function
        create_args = []
        update_args = []
        ser_args = []
        update_field_funcs: list[Callable[[AST], Any]] = []

        for prop in cls.properties.values():
            if prop.is_private:
                # skip private fields as this is for APIs exchange
                continue

            if isinstance(prop, DataProperty):
                tstype = prop.datatype.get_typescript_type()
                if tstype.dep is not None:
                    program.import_(tstype.dep, True)

                propname = to_camel_case(prop.name)
                # however, if this is a primary key and auto-increment, we set a different default value
                # to be -1 to avoid start from 0
                if (
                    prop.db is not None
                    and prop.db.is_primary_key
                    and prop.db.is_auto_increment
                ):
                    propvalue = expr.ExprConstant(-1)
                else:
                    propvalue = tstype.get_default()

                if prop.db is not None and prop.db.is_primary_key:
                    cls_pk = (expr.ExprIdent(propname), propvalue)

                create_args.append((expr.ExprIdent(propname), propvalue))
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
                update_args.append(
                    (
                        expr.ExprIdent(propname),
                        PredefinedFn.attr_getter(
                            expr.ExprIdent("record"), expr.ExprIdent(propname)
                        ),
                    )
                )
                ser_args.append(
                    (
                        expr.ExprIdent(prop.name),
                        PredefinedFn.attr_getter(
                            expr.ExprIdent("this"), expr.ExprIdent(propname)
                        ),
                    )
                )
                if not (prop.db is not None and prop.db.is_primary_key):
                    # skip observable for primary key as it is not needed
                    observable_args.append(
                        (
                            expr.ExprIdent(propname),
                            expr.ExprIdent("observable"),
                        )
                    )
                    observable_args.append(
                        (
                            expr.ExprIdent(f"update{to_pascal_case(prop.name)}"),
                            expr.ExprIdent("action"),
                        )
                    )

                def _update_field_func(prop, propname, tstype, draft_clsname):
                    return lambda ast: ast(
                        stmt.LineBreak(),
                        lambda ast01: ast01.func(
                            f"update{to_pascal_case(prop.name)}",
                            [
                                DeferredVar.simple(
                                    "value",
                                    expr.ExprIdent(tstype.type),
                                ),
                            ],
                            expr.ExprIdent(draft_clsname),
                            comment=f"Update the `{prop.name}` field",
                        )(
                            stmt.AssignStatement(
                                PredefinedFn.attr_getter(
                                    expr.ExprIdent("this"), expr.ExprIdent(propname)
                                ),
                                expr.ExprIdent("value"),
                            ),
                            stmt.AssignStatement(
                                PredefinedFn.attr_getter(
                                    expr.ExprIdent("this"), expr.ExprIdent("stale")
                                ),
                                expr.ExprConstant(True),
                            ),
                            stmt.ReturnStatement(expr.ExprIdent("this")),
                        ),
                    )

                update_field_funcs.append(
                    _update_field_func(prop, propname, tstype, draft_clsname)
                )

        prop_defs.append(stmt.DefClassVarStatement("stale", "boolean"))
        prop_constructor_assigns.append(
            stmt.AssignStatement(
                PredefinedFn.attr_getter(
                    expr.ExprIdent("this"), expr.ExprIdent("stale")
                ),
                expr.ExprIdent("args.stale"),
            )
        )
        observable_args.append(
            (
                expr.ExprIdent("stale"),
                expr.ExprIdent("observable"),
            )
        )
        create_args.append(
            (
                expr.ExprIdent("stale"),
                expr.ExprConstant(True),
            ),
        )
        update_args.append(
            (
                expr.ExprIdent("stale"),
                expr.ExprConstant(False),
            ),
        )
        observable_args.sort(key=lambda x: {"observable": 0, "action": 1}[x[1].ident])
        program.root(
            lambda ast00: ast00.interface(
                draft_clsname + "ConstructorArgs",
            )(*prop_defs),
            stmt.LineBreak(),
            lambda ast10: ast10.class_(draft_clsname)(
                *prop_defs,
                stmt.LineBreak(),
                lambda ast10: ast10.func(
                    "constructor",
                    [
                        DeferredVar.simple(
                            "args",
                            expr.ExprIdent(draft_clsname + "ConstructorArgs"),
                        ),
                    ],
                )(
                    *prop_constructor_assigns,
                    stmt.LineBreak(),
                    stmt.SingleExprStatement(
                        expr.ExprFuncCall(
                            expr.ExprIdent("makeObservable"),
                            [
                                expr.ExprIdent("this"),
                                PredefinedFn.dict(observable_args),
                            ],
                        )
                    ),
                ),
                stmt.LineBreak(),
                lambda ast11: (
                    ast11.func(
                        "is_new_record",
                        [],
                        expr.ExprIdent("boolean"),
                        comment="Check if this draft is for creating a new record",
                    )(
                        stmt.ReturnStatement(
                            expr.ExprEqual(
                                PredefinedFn.attr_getter(
                                    expr.ExprIdent("this"), cls_pk[0]
                                ),
                                cls_pk[1],
                            )
                        )
                    )
                    if cls_pk is not None
                    else None
                ),
                stmt.LineBreak(),
                lambda ast12: ast12.func(
                    "create",
                    [],
                    expr.ExprIdent(draft_clsname),
                    is_static=True,
                    comment="Make a new draft for creating a new record",
                )(
                    stmt.ReturnStatement(
                        expr.ExprNewInstance(
                            expr.ExprIdent(draft_clsname),
                            [PredefinedFn.dict(create_args)],
                        )
                    ),
                ),
                stmt.LineBreak(),
                lambda ast13: ast13.func(
                    "update",
                    [DeferredVar.simple("record", expr.ExprIdent(cls.name))],
                    expr.ExprIdent(draft_clsname),
                    is_static=True,
                    comment="Make a new draft for updating an existing record",
                )(
                    stmt.ReturnStatement(
                        expr.ExprNewInstance(
                            expr.ExprIdent(draft_clsname),
                            [PredefinedFn.dict(update_args)],
                        )
                    ),
                ),
                *update_field_funcs,
                stmt.LineBreak(),
                lambda ast14: ast14.func(
                    "ser",
                    [],
                    expr.ExprIdent("any"),
                    comment="Serialize the draft to communicate with the server",
                )(
                    stmt.ReturnStatement(
                        PredefinedFn.dict(ser_args),
                    ),
                ),
            ),
        )

        pkg.module("Draft" + cls.name).write(program)

    for cls in schema.topological_sort():
        pkg = target_pkg.pkg(cls.name[0].lower() + cls.name[1:])
        make_normal(cls, pkg)
        make_draft(cls, pkg)
