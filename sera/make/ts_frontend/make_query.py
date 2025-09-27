from __future__ import annotations

from codegen.models import AST, ImportHelper, PredefinedFn, Program, expr, stmt
from codegen.models.var import DeferredVar
from loguru import logger

from sera.misc import (
    assert_isinstance,
    assert_not_null,
    identity,
    to_camel_case,
    to_pascal_case,
    to_snake_case,
)
from sera.models import (
    Class,
    DataProperty,
    Enum,
    ObjectProperty,
    Package,
    Schema,
    TsTypeWithDep,
)


def make_query(schema: Schema, cls: Class, pkg: Package):
    """Make query processor and query schema.

    Args:
        schema: The overall schema of the application, which contains all classes & enums
        cls: The class that we want to generate the query processor and schema
        pkg: The output package (directory) for the class in the `@.models` package. For example, if the
            class is `User`, then the package would be `src/models/user`.

    Returns:
        This function do not return anything as it writes the query helper directly to a file.
    """
    if not cls.is_public:
        # skip classes that are not public
        return

    outmod = pkg.module(cls.name + "Query")

    program = Program()
    program.import_(f"@.models.{pkg.dir.name}.{cls.name}.{cls.name}", True)
    program.import_(f"sera-db.QueryProcessor", True)
    program.import_(f"sera-db.Query", True)

    query_args = []
    for prop in cls.properties.values():
        pypropname = prop.name
        tspropname = to_camel_case(prop.name)

        if isinstance(prop, ObjectProperty) and prop.target.db is not None:
            tspropname = tspropname + "Id"
            pypropname = prop.name + "_id"

        if tspropname != pypropname:
            query_args.append(
                (
                    expr.ExprIdent(tspropname),
                    expr.ExprConstant(pypropname),
                )
            )

    query_condition_args = []
    for prop in cls.properties.values():
        if prop.db is None or prop.data.is_private:
            # This property is not stored in the database or it's private, so we skip it
            continue
        if (
            isinstance(prop, DataProperty)
            and prop.db is not None
            and not prop.db.is_indexed
        ):
            # This property is not indexed, so we skip it
            continue
        if isinstance(prop, ObjectProperty) and prop.target.db is None:
            # TODO: Implement this! This property is an embedded object property, we need to figure out
            # which necessary properties are queryable and add them to the field names
            continue

        tspropname = to_camel_case(prop.name)
        if isinstance(prop, ObjectProperty) and prop.target.db is not None:
            # This property is an object property stored in the database, "Id" is added to the property name
            tspropname = tspropname + "Id"

        if isinstance(prop, DataProperty):
            tstype = prop.datatype.get_typescript_type()
        else:
            assert isinstance(prop, ObjectProperty)
            tstype = assert_not_null(
                prop.target.get_id_property()
            ).datatype.get_typescript_type()

        for dep in tstype.deps:
            program.import_(dep, is_import_attr=True)

        query_ops = []

        if tstype.type == "string":
            query_ops.append(('"fuzzy"', tstype.type))
        elif tstype.type == "number":
            if (
                isinstance(prop, DataProperty)
                and prop.db is not None
                and prop.db.is_primary_key
            ) or (isinstance(prop, ObjectProperty) and prop.target.db is not None):
                # primary key or foreign key, we only support a limited set of operations
                query_ops.append(('"eq" | "ne"', tstype.type))
            else:
                query_ops.append(
                    ('"eq" | "ne" | "lt" | "lte" | "gt" | "gte"', tstype.type)
                )
                query_ops.append(('"bti"', "[number, number]"))
        elif tstype.is_enum_type():
            query_ops.append(('"eq" | "ne"', tstype.type))
        elif tstype.type == "Date":
            # for date type, we use iso string as the value
            query_ops.append(('"eq" | "ne" | "lt" | "lte" | "gt" | "gte"', "string"))
            query_ops.append(('"bti"', "[string, string]"))
        else:
            raise NotImplementedError(tstype.type)

        query_condition_args.append(
            (
                expr.ExprIdent(tspropname + "?"),
                expr.ExprRawTypescript(
                    " | ".join(
                        [
                            PredefinedFn.dict(
                                [
                                    (expr.ExprIdent("op"), expr.ExprIdent(op)),
                                    (expr.ExprIdent("value"), expr.ExprIdent(value)),
                                ]
                            ).to_typescript()
                            for op, value in query_ops
                        ]
                    )
                ),
            )
        )

    program.root(
        stmt.LineBreak(),
        stmt.TypescriptStatement(
            f"export const query = "
            + expr.ExprNewInstance(
                expr.ExprIdent(f"QueryProcessor<{cls.name}>"),
                [
                    PredefinedFn.dict(query_args),
                ],
            ).to_typescript()
            + ";",
        ),
        stmt.LineBreak(),
        stmt.TypescriptStatement(
            f"export type {cls.name}Query = Query<{cls.name}, "
            + PredefinedFn.dict(query_condition_args).to_typescript()
            + ">;"
        ),
    )

    outmod.write(program)
