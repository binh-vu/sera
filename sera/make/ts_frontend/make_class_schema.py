from __future__ import annotations

from codegen.models import ImportHelper, PredefinedFn, Program, expr, stmt

from sera.make.ts_frontend.misc import TS_GLOBAL_IDENTS, get_normalizer
from sera.misc import assert_not_null, to_camel_case, to_pascal_case
from sera.models import (
    Class,
    DataProperty,
    Enum,
    ObjectProperty,
    Package,
    Schema,
    TsTypeWithDep,
)
from sera.typing import is_set


def make_class_schema(schema: Schema, cls: Class, pkg: Package):
    """Make schema definition for the class in frontend so that components can use this information select
    appropriate components to display or edit the data.

    Args:
        schema: The overall schema of the application, which contains all classes & enums
        cls: The class that we want to generate the schema
        pkg: The output package (directory) for the class in the `@.models` package. For example, if the
            class is `User`, then the package would be `src/models/user`.

    Returns:
        This function do not return anything as it writes the schema directly to a file.
    """
    if not cls.is_public:
        # skip classes that are not public
        return

    program = Program()
    prop_defs: list[tuple[DataProperty | ObjectProperty, expr.Expr, expr.Expr]] = []
    prop_normalizers: list[tuple[expr.Expr, expr.Expr]] = []

    import_helper = ImportHelper(program, TS_GLOBAL_IDENTS)

    for prop in cls.properties.values():
        # we must include private properties that are needed during upsert for our forms.
        # if prop.data.is_private:
        #     # skip private fields as this is for APIs exchange
        #     continue
        tspropname = to_camel_case(prop.name)
        pypropname = prop.name
        if isinstance(prop, ObjectProperty) and prop.target.db is not None:
            # this is a database object, we append id to the property name
            tspropname = tspropname + "Id"
            pypropname = prop.name + "_id"

        tsprop = {}

        if isinstance(prop, DataProperty):
            tstype = prop.get_data_model_datatype().get_typescript_type()
            # for schema definition, we need to use the original type, not the type alias
            # if prop.name == idprop.name:
            #     # use id type alias
            #     tstype = TsTypeWithDep(f"{cls.name}Id")
            for dep in tstype.deps:
                program.import_(dep, True)
            tsprop = [
                (
                    expr.ExprIdent("datatype"),
                    (
                        expr.ExprConstant(tstype.spectype)
                        if tstype.type not in schema.enums
                        else expr.ExprConstant("enum")
                    ),
                ),
                *(
                    [
                        (
                            expr.ExprIdent("enumType"),
                            export_enum_info(program, schema.enums[tstype.type]),
                        )
                    ]
                    if tstype.type in schema.enums
                    else []
                ),
                *(
                    [
                        (
                            expr.ExprIdent("foreignKeyTarget"),
                            expr.ExprConstant(prop.db.foreign_key.name),
                        )
                    ]
                    if prop.db is not None
                    and prop.db.is_primary_key
                    and prop.db.foreign_key is not None
                    else []
                ),
                (
                    expr.ExprIdent("isRequired"),
                    expr.ExprConstant(
                        not prop.is_optional
                        and prop.default_value is None
                        and prop.default_factory is None
                    ),
                ),
            ]

            norm_func = get_normalizer(tstype, import_helper)
            if norm_func is not None:
                # we have a normalizer for this type
                prop_normalizers.append((expr.ExprIdent(tspropname), norm_func))
        else:
            assert isinstance(prop, ObjectProperty)
            if prop.target.db is not None:
                # this class is stored in the database, we store the id instead
                tstype = (
                    assert_not_null(prop.target.get_id_property())
                    .get_data_model_datatype()
                    .get_typescript_type()
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

            # we don't store the type itself, but just the name of the type
            # so not need to import the dependency
            # if tstype.dep is not None:
            #     program.import_(
            #         tstype.dep,
            #         True,
            #     )

            tsprop = [
                (
                    expr.ExprIdent("targetClass"),
                    expr.ExprConstant(prop.target.name),
                ),
                (
                    expr.ExprIdent("datatype"),
                    expr.ExprConstant(
                        tstype.spectype if prop.target.db is not None else "undefined"
                    ),
                ),
                (
                    expr.ExprIdent("cardinality"),
                    expr.ExprConstant(prop.cardinality.value),
                ),
                (
                    expr.ExprIdent("isEmbedded"),
                    expr.ExprConstant(prop.target.db is None),
                ),
                (
                    expr.ExprIdent("isRequired"),
                    expr.ExprConstant(not prop.is_optional),
                ),
            ]

        prop_defs.append(
            (
                prop,
                expr.ExprIdent(tspropname),
                PredefinedFn.dict(
                    [
                        (expr.ExprIdent("name"), expr.ExprConstant(pypropname)),
                        (expr.ExprIdent("tsName"), expr.ExprConstant(tspropname)),
                        (
                            expr.ExprIdent("updateFuncName"),
                            expr.ExprConstant(f"update{to_pascal_case(prop.name)}"),
                        ),
                        (
                            expr.ExprIdent("label"),
                            expr.ExprConstant(prop.label.to_dict()),
                        ),
                        (
                            expr.ExprIdent("description"),
                            (
                                expr.ExprConstant(prop.description.to_dict())
                                if not prop.description.is_empty()
                                else expr.ExprConstant("undefined")
                            ),
                        ),
                        (
                            expr.ExprIdent("constraints"),
                            PredefinedFn.list(
                                [
                                    expr.ExprConstant(
                                        constraint.get_typescript_constraint()
                                    )
                                    for constraint in prop.data.constraints
                                ]
                            ),
                        ),
                    ]
                    + tsprop
                ),
            )
        )

    for type in ["ObjectProperty", "DataProperty"]:
        program.import_(f"sera-db.{type}", True)
    if cls.db is not None:
        program.import_(f"sera-db.Schema", True)
    else:
        program.import_(f"sera-db.EmbeddedSchema", True)

    program.import_(f"@.models.{pkg.dir.name}.{cls.name}.{cls.name}", True)
    program.import_(f"@.models.{pkg.dir.name}.Draft{cls.name}.Draft{cls.name}", True)
    program.import_(
        f"@.models.{pkg.dir.name}.Draft{cls.name}.draft{cls.name}Validators", True
    )
    if cls.db is not None:
        program.import_(f"@.models.{pkg.dir.name}.{cls.name}.{cls.name}Id", True)

    program.root(
        stmt.LineBreak(),
        stmt.TypescriptStatement(
            f"export type {cls.name}SchemaType = "
            + PredefinedFn.dict(
                (
                    [
                        (expr.ExprIdent("id"), expr.ExprIdent(f"{cls.name}Id")),
                    ]
                    if cls.db is not None
                    else []
                )
                + [
                    (
                        expr.ExprIdent("publicProperties"),
                        expr.ExprIdent(
                            " | ".join(
                                [
                                    expr.ExprConstant(
                                        to_camel_case(prop.name) + "Id"
                                        if isinstance(prop, ObjectProperty)
                                        and prop.target.db is not None
                                        else to_camel_case(prop.name)
                                    ).to_typescript()
                                    for prop in cls.properties.values()
                                    if not prop.data.is_private
                                ]
                            )
                        ),
                    ),
                    (
                        expr.ExprIdent("allProperties"),
                        expr.ExprIdent(
                            f"{cls.name}SchemaType['publicProperties']"
                            + (
                                " | "
                                + " | ".join(
                                    [
                                        expr.ExprConstant(
                                            to_camel_case(prop.name)
                                        ).to_typescript()
                                        for prop in cls.properties.values()
                                        if prop.data.is_private
                                    ]
                                )
                                if any(
                                    prop.data.is_private
                                    for prop in cls.properties.values()
                                )
                                else ""
                            )
                        ),
                    ),
                    (
                        expr.ExprIdent("cls"),
                        expr.ExprIdent(cls.name),
                    ),
                    (
                        expr.ExprIdent("draftCls"),
                        expr.ExprIdent(f"Draft{cls.name}"),
                    ),
                ]
            ).to_typescript()
            + ";",
        ),
        stmt.LineBreak(),
        stmt.TypescriptStatement(
            f"const publicProperties: Record<{cls.name}SchemaType['publicProperties'], DataProperty | ObjectProperty> = "
            + PredefinedFn.dict(
                [
                    (prop_name, prop_def)
                    for prop, prop_name, prop_def in prop_defs
                    if not prop.data.is_private
                ]
            ).to_typescript()
            + ";"
        ),
        stmt.LineBreak(),
        stmt.TypescriptStatement(
            (
                f"export const {cls.name}Schema: Schema<{cls.name}SchemaType['id'], {cls.name}SchemaType['cls'], {cls.name}SchemaType['draftCls'], {cls.name}SchemaType['publicProperties'], {cls.name}SchemaType['allProperties'], {cls.name}SchemaType> = "
                if cls.db is not None
                else f"export const {cls.name}Schema: EmbeddedSchema<{cls.name}SchemaType['cls'], {cls.name}SchemaType['draftCls'], {cls.name}SchemaType['publicProperties'], {cls.name}SchemaType['allProperties']> = "
            )
            + PredefinedFn.dict(
                [
                    (
                        expr.ExprIdent("publicProperties"),
                        expr.ExprIdent("publicProperties"),
                    ),
                    (
                        expr.ExprIdent("allProperties"),
                        expr.ExprIdent(
                            "{ ...publicProperties, "
                            + ", ".join(
                                [
                                    f"{prop_name.to_typescript()}: {prop_def.to_typescript()}"
                                    for prop, prop_name, prop_def in prop_defs
                                    if prop.data.is_private
                                ]
                            )
                            + "}"
                        ),
                    ),
                    (
                        expr.ExprIdent("validators"),
                        expr.ExprIdent(f"draft{cls.name}Validators"),
                    ),
                    (
                        expr.ExprIdent("normalizers"),
                        PredefinedFn.dict(prop_normalizers),
                    ),
                ]
                + (
                    [
                        (
                            expr.ExprIdent("primaryKey"),
                            expr.ExprConstant(
                                assert_not_null(cls.get_id_property()).name
                            ),
                        )
                    ]
                    if cls.db is not None
                    else []
                )
            ).to_typescript()
            + ";"
        ),
    )
    pkg.module(cls.name + "Schema").write(program)


def export_enum_info(program: Program, enum: Enum) -> expr.Expr:
    """Export enum information to

    ```
    {
        type: <EnumType>,
        label: { [value]: MultiLingualString },
        description: { [value]: MultiLingualString }
    }
    ```
    """
    for key in ["Label", "Description"]:
        program.import_(f"@.models.enums.{enum.name}{key}", True)

    return PredefinedFn.dict(
        [
            (expr.ExprIdent("type"), expr.ExprIdent(enum.name)),
            (expr.ExprIdent("label"), expr.ExprIdent(enum.name + "Label")),
            (expr.ExprIdent("description"), expr.ExprIdent(enum.name + "Description")),
        ]
    )
