from __future__ import annotations

from typing import Callable, Literal, Optional, Sequence

from codegen.models import (
    AST,
    DeferredVar,
    ImportHelper,
    PredefinedFn,
    Program,
    expr,
    stmt,
)

from sera.misc import (
    assert_isinstance,
    assert_not_null,
    filter_duplication,
    to_snake_case,
)
from sera.models import (
    Cardinality,
    Class,
    DataProperty,
    ObjectProperty,
    Package,
    PyTypeWithDep,
    Schema,
)
from sera.typing import GLOBAL_IDENTS, ObjectPath


def make_python_enums(
    schema: Schema,
    target_pkg: Package,
    reference_objects: dict[str, ObjectPath],
):
    """Make enums defined in the schema.

    Args:
        schema: The schema to generate the classes from.
        target_pkg: The package to write the enums to.
        reference_objects: A dictionary of objects to their references (e.g., the ones that are defined outside and used as referenced such as Tenant).
    """
    for enum in schema.enums.values():
        if enum.name in reference_objects:
            # skip enums that are defined in different apps
            continue

        program = Program()
        program.import_("__future__.annotations", True)
        program.import_("enum.Enum", True)

        enum_values = []
        for value in enum.values.values():
            enum_values.append(
                stmt.DefClassVarStatement(
                    name=value.name,
                    type=None,
                    value=expr.ExprConstant(value.value),
                )
            )

        program.root(
            stmt.LineBreak(),
            lambda ast: ast.class_(
                enum.name,
                (
                    [expr.ExprIdent("str")]
                    if enum.is_str_enum()
                    else [expr.ExprIdent("int")]
                )
                + [expr.ExprIdent("Enum")],
            )(*enum_values),
        )

        target_pkg.module(enum.get_pymodule_name()).write(program)


def make_python_data_model(
    schema: Schema, target_pkg: Package, reference_classes: dict[str, ObjectPath]
):
    """Generate public classes for the API from the schema.

    Args:
        schema: The schema to generate the classes from.
        target_pkg: The package to write the classes to.
        reference_classes: A dictionary of class names to their references (e.g., the ones that are defined outside and used as referenced such as Tenant).
    """
    app = target_pkg.app

    def from_db_type_conversion(
        record: expr.ExprIdent,
        prop: DataProperty | ObjectProperty,
        value_pass_as_args: Optional[expr.Expr] = None,
    ):
        """Convert the value from the database to the data model type.

        Args:
            record: The record to convert from.
            prop: The property to convert.
            value_pass_as_args: If provided, this value will be used instead of getting the value from the record. This is useful for functions that
                receive the column value as an argument, such as the `as_composite` function.
        """
        if value_pass_as_args is not None:
            value = value_pass_as_args
            assert record == expr.ExprIdent(
                ""
            ), "If value_pass_as_args is provided, record should not be used as a dummy value should be passed instead."
        else:
            value = PredefinedFn.attr_getter(record, expr.ExprIdent(prop.name))
        if isinstance(prop, ObjectProperty) and prop.target.db is not None:
            if prop.cardinality.is_star_to_many():
                value = PredefinedFn.map_list(
                    value,
                    lambda item: PredefinedFn.attr_getter(
                        item, expr.ExprIdent(prop.name + "_id")
                    ),
                )
            else:
                assert (
                    value_pass_as_args is None
                ), "Cannot use value_pass_as_args for a single object property."
                value = PredefinedFn.attr_getter(
                    record, expr.ExprIdent(prop.name + "_id")
                )

            target_idprop = assert_not_null(prop.target.get_id_property())
            conversion_fn = get_data_conversion(
                target_idprop.datatype.get_python_type().type,
                target_idprop.get_data_model_datatype().get_python_type().type,
            )
            value = conversion_fn(value)
        elif isinstance(prop, DataProperty) and prop.is_diff_data_model_datatype():
            value = get_data_conversion(
                prop.datatype.get_python_type().type,
                prop.get_data_model_datatype().get_python_type().type,
            )(value)

        return value

    def to_db_type_conversion(
        program: Program,
        slf: expr.ExprIdent,
        cls: Class,
        mode: Literal["create", "update"],
        prop: DataProperty | ObjectProperty,
    ):
        value = PredefinedFn.attr_getter(slf, expr.ExprIdent(prop.name))
        if isinstance(prop, ObjectProperty):
            if (
                prop.target.db is not None
                and prop.cardinality == Cardinality.MANY_TO_MANY
            ):
                # we have to use the associated object
                # if this isn't a many-to-many relationship, we only keep the id, so no need to convert to the type.
                AssociationTable = f"{cls.name}{prop.target.name}"
                program.import_(
                    app.models.db.path
                    + f".{to_snake_case(AssociationTable)}.{AssociationTable}",
                    True,
                )

                target_idprop = assert_not_null(prop.target.get_id_property())
                conversion_fn = get_data_conversion(
                    target_idprop.get_data_model_datatype().get_python_type().type,
                    target_idprop.datatype.get_python_type().type,
                )

                return PredefinedFn.map_list(
                    value,
                    lambda item: expr.ExprFuncCall(
                        expr.ExprIdent(AssociationTable),
                        [
                            PredefinedFn.keyword_assignment(
                                f"{prop.name}_id", conversion_fn(item)
                            )
                        ],
                    ),
                )
            elif prop.target.db is None:
                # if the target class is not in the database, we need to convert the value to the python type used in db.
                # if the cardinality is many-to-many, we need to convert each item in the list.
                if prop.cardinality.is_star_to_many():
                    value = PredefinedFn.map_list(
                        value, lambda item: expr.ExprMethodCall(item, "to_db", [])
                    )
                else:
                    value = expr.ExprMethodCall(value, "to_db", [])
        elif isinstance(prop, DataProperty) and prop.is_diff_data_model_datatype():
            # convert the value to the python type used in db
            converted_value = get_data_conversion(
                prop.get_data_model_datatype().get_python_type().type,
                prop.datatype.get_python_type().type,
            )(value)

            if mode == "update" and prop.data.is_private:
                # if the property is private and it's UNSET, we cannot transform it to the database type
                # and has to use the UNSET value (the update query will ignore this field)
                program.import_("sera.typing.UNSET", True)
                program.import_("sera.typing.is_set", True)
                value = expr.ExprTernary(
                    expr.ExprFuncCall(expr.ExprIdent("is_set"), [value]),
                    converted_value,
                    expr.ExprIdent("UNSET"),
                )
            else:
                value = converted_value
        return value

    def make_uscp_func(
        cls: Class,
        mode: Literal["create", "update"],
        ast: AST,
        ident_manager: ImportHelper,
    ):
        func = ast.func(
            "update_system_controlled_props",
            [
                DeferredVar.simple("self"),
                DeferredVar.simple(
                    "conn",
                    ident_manager.use("ASGIConnection"),
                ),
            ],
        )

        assign_user = False

        for prop in cls.properties.values():
            if prop.data.system_controlled is None:
                continue

            update_func = None
            if mode == "create":
                if prop.data.system_controlled.on_create_bypass is not None:
                    # by-pass the update function are handled later
                    continue

                if prop.data.system_controlled.is_on_create_value_updated():
                    update_func = (
                        prop.data.system_controlled.get_on_create_update_func()
                    )
            else:
                if prop.data.system_controlled.on_update_bypass is not None:
                    # by-pass the update function are handled later
                    continue
                if prop.data.system_controlled.is_on_update_value_updated():
                    update_func = (
                        prop.data.system_controlled.get_on_update_update_func()
                    )

            if update_func is None:
                continue

            if update_func.func == "getattr":
                if update_func.args[0] == "user":
                    if len(update_func.args) != 2:
                        raise NotImplementedError(
                            f"Unsupported update function: {update_func.func} with args {update_func.args}"
                        )
                    if not assign_user:
                        func(
                            stmt.AssignStatement(
                                expr.ExprIdent("user"),
                                PredefinedFn.item_getter(
                                    PredefinedFn.attr_getter(
                                        expr.ExprIdent("conn"),
                                        expr.ExprIdent("scope"),
                                    ),
                                    expr.ExprConstant("user"),
                                ),
                            )
                        )
                        assign_user = True
                    epr = PredefinedFn.attr_getter(
                        expr.ExprIdent("user"), expr.ExprIdent(update_func.args[1])
                    )
                elif update_func.args[0] == "self":
                    epr = PredefinedFn.attr_getter(
                        expr.ExprIdent("self"), expr.ExprIdent(update_func.args[1])
                    )
                else:
                    raise NotImplementedError(
                        f"Unsupported update function: {update_func.func} with args {update_func.args}"
                    )
            else:
                raise NotImplementedError(update_func.func)

            smt = stmt.AssignStatement(
                PredefinedFn.attr_getter(
                    expr.ExprIdent("self"), expr.ExprIdent(prop.name)
                ),
                epr,
            )
            func(smt)

        # handle the by-pass properties here
        for prop in cls.properties.values():
            if prop.data.system_controlled is None:
                continue

            update_func = None
            if mode == "create":
                if prop.data.system_controlled.on_create_bypass is None:
                    # non by-pass the update function are handled earlier
                    continue

                if prop.data.system_controlled.is_on_create_value_updated():
                    update_func = (
                        prop.data.system_controlled.get_on_create_update_func()
                    )
            else:
                if prop.data.system_controlled.on_update_bypass is None:
                    # non by-pass the update function are handled earlier
                    continue

                if prop.data.system_controlled.is_on_update_value_updated():
                    update_func = (
                        prop.data.system_controlled.get_on_update_update_func()
                    )

            if update_func is None:
                continue

            raise NotImplementedError("We haven't handled the by-pass properties yet.")

        func(
            stmt.AssignStatement(
                PredefinedFn.attr_getter(
                    expr.ExprIdent("self"), expr.ExprIdent("_is_scp_updated")
                ),
                expr.ExprConstant(True),
            )
        )

    def make_create(program: Program, cls: Class):
        program.import_("__future__.annotations", True)
        program.import_("msgspec", False)
        if cls.db is not None:
            # if the class is stored in the database, we need to import the database module
            program.import_(
                app.models.db.path + f".{cls.get_pymodule_name()}.{cls.name}",
                True,
                alias=f"{cls.name}DB",
            )

        ident_manager = ImportHelper(
            program,
            GLOBAL_IDENTS,
        )

        is_on_create_value_updated = any(
            prop.data.system_controlled is not None
            and prop.data.system_controlled.is_on_create_value_updated()
            for prop in cls.properties.values()
        )
        program.root.linebreak()
        cls_ast = program.root.class_(
            "Create" + cls.name,
            [expr.ExprIdent("msgspec.Struct"), expr.ExprIdent("kw_only=True")],
        )
        for prop in cls.properties.values():
            # Skip fields that are system-controlled (e.g., cached or derived fields)
            # and cannot be updated based on information parsed from the request.
            if (
                prop.data.system_controlled is not None
                and prop.data.system_controlled.is_on_create_ignored()
            ):
                continue

            if isinstance(prop, DataProperty):
                pytype = prop.get_data_model_datatype().get_python_type().clone()
                if len(prop.data.constraints) > 0:
                    # if the property has constraints, we need to figure out
                    program.import_("typing.Annotated", True)
                    if len(prop.data.constraints) == 1:
                        pytype.type = "Annotated[%s, %s]" % (
                            pytype.type,
                            prop.data.constraints[0].get_msgspec_constraint(),
                        )
                    else:
                        raise NotImplementedError(prop.data.constraints)

                if prop.is_optional:
                    pytype = pytype.as_optional_type()

                for dep in pytype.deps:
                    program.import_(dep, True)

                # private property are available for creating, but not for updating.
                # so we do not need to skip it.
                # if prop.data.is_private:
                #     program.import_("typing.Union", True)
                #     program.import_("sera.typing.UnsetType", True)
                #     program.import_("sera.typing.UNSET", True)
                #     pytype_type = f"Union[{pytype_type}, UnsetType]"

                prop_default_value = None
                # if prop.data.is_private:
                #     prop_default_value = expr.ExprIdent("UNSET")
                if prop.default_value is not None:
                    prop_default_value = expr.ExprConstant(prop.default_value)
                elif prop.default_factory is not None:
                    program.import_(prop.default_factory.pyfunc, True)
                    prop_default_value = expr.ExprFuncCall(
                        expr.ExprIdent("msgspec.field"),
                        [
                            PredefinedFn.keyword_assignment(
                                "default_factory",
                                expr.ExprIdent(prop.default_factory.pyfunc),
                            )
                        ],
                    )

                cls_ast(
                    stmt.DefClassVarStatement(
                        prop.name, pytype.type, prop_default_value
                    )
                )
            elif isinstance(prop, ObjectProperty):
                if prop.target.db is not None:
                    # if the target class is in the database, we expect the user to pass the foreign key for it.
                    pytype = (
                        assert_not_null(prop.target.get_id_property())
                        .get_data_model_datatype()
                        .get_python_type()
                    )
                else:
                    pytype = PyTypeWithDep(
                        f"Create{prop.target.name}",
                        [
                            f"{target_pkg.module(prop.target.get_pymodule_name()).path}.Create{prop.target.name}"
                        ],
                    )

                if prop.cardinality.is_star_to_many():
                    pytype = pytype.as_list_type()
                elif prop.is_optional:
                    pytype = pytype.as_optional_type()

                for dep in pytype.deps:
                    program.import_(dep, True)

                cls_ast(stmt.DefClassVarStatement(prop.name, pytype.type))

        if is_on_create_value_updated:
            program.import_("typing.Optional", True)
            program.import_("sera.typing.is_set", True)
            cls_ast(
                stmt.Comment(
                    "A marker to indicate that the system-controlled properties are updated"
                ),
                stmt.DefClassVarStatement(
                    "_is_scp_updated", "bool", expr.ExprConstant(False)
                ),
                stmt.LineBreak(),
                lambda ast: ast.func(
                    "__post_init__",
                    [
                        DeferredVar.simple("self"),
                    ],
                )(
                    stmt.AssignStatement(
                        PredefinedFn.attr_getter(
                            expr.ExprIdent("self"), expr.ExprIdent("_is_scp_updated")
                        ),
                        expr.ExprConstant(False),
                    ),
                ),
                stmt.LineBreak(),
                lambda ast: make_uscp_func(cls, "create", ast, ident_manager),
            )

        cls_ast(
            stmt.LineBreak(),
            lambda ast00: ast00.func(
                "to_db",
                [
                    DeferredVar.simple("self"),
                ],
                return_type=expr.ExprIdent(
                    f"{cls.name}DB" if cls.db is not None else cls.name
                ),
            )(
                (
                    stmt.AssertionStatement(
                        PredefinedFn.attr_getter(
                            expr.ExprIdent("self"),
                            expr.ExprIdent("_is_scp_updated"),
                        ),
                        expr.ExprConstant(
                            "The model data must be verified before converting to db model"
                        ),
                    )
                    if is_on_create_value_updated
                    else None
                ),
                lambda ast10: ast10.return_(
                    expr.ExprFuncCall(
                        expr.ExprIdent(
                            f"{cls.name}DB" if cls.db is not None else cls.name
                        ),
                        [
                            (
                                ident_manager.use("UNSET")
                                if prop.data.system_controlled is not None
                                and prop.data.system_controlled.is_on_create_ignored()
                                else to_db_type_conversion(
                                    program, expr.ExprIdent("self"), cls, "create", prop
                                )
                            )
                            for prop in cls.properties.values()
                        ],
                    )
                ),
            ),
        )

    def make_update(program: Program, cls: Class):
        program.import_("__future__.annotations", True)
        program.import_("msgspec", False)
        if cls.db is not None:
            # if the class is stored in the database, we need to import the database module
            program.import_(
                app.models.db.path + f".{cls.get_pymodule_name()}.{cls.name}",
                True,
                alias=f"{cls.name}DB",
            )

        ident_manager = ImportHelper(
            program,
            GLOBAL_IDENTS,
        )

        # property that normal users cannot set, but super users can
        is_on_update_value_updated = any(
            prop.data.system_controlled is not None
            and prop.data.system_controlled.is_on_update_value_updated()
            for prop in cls.properties.values()
        )

        program.root.linebreak()
        cls_ast = program.root.class_(
            "Update" + cls.name,
            [expr.ExprIdent("msgspec.Struct"), expr.ExprIdent("kw_only=True")],
        )
        for prop in cls.properties.values():
            # Skip fields that are system-controlled (e.g., cached or derived fields)
            # and cannot be updated based on information parsed from the request.
            if (
                prop.data.system_controlled is not None
                and prop.data.system_controlled.is_on_update_ignored()
            ):
                continue

            if isinstance(prop, DataProperty):
                pytype = prop.get_data_model_datatype().get_python_type().clone()

                if len(prop.data.constraints) > 0:
                    # if the property has constraints, we need to figure out
                    program.import_("typing.Annotated", True)
                    if len(prop.data.constraints) == 1:
                        pytype.type = "Annotated[%s, %s]" % (
                            pytype.type,
                            prop.data.constraints[0].get_msgspec_constraint(),
                        )
                    else:
                        raise NotImplementedError(prop.data.constraints)

                if prop.is_optional:
                    pytype = pytype.as_optional_type()

                for dep in pytype.deps:
                    program.import_(dep, True)

                if prop.data.is_private:
                    program.import_("typing.Union", True)
                    program.import_("sera.typing.UnsetType", True)
                    program.import_("sera.typing.UNSET", True)
                    pytype.type = f"Union[{pytype.type}, UnsetType]"

                prop_default_value = None
                if prop.data.is_private:
                    prop_default_value = expr.ExprIdent("UNSET")
                elif prop.default_value is not None:
                    prop_default_value = expr.ExprConstant(prop.default_value)
                elif prop.default_factory is not None:
                    program.import_(prop.default_factory.pyfunc, True)
                    prop_default_value = expr.ExprFuncCall(
                        expr.ExprIdent("msgspec.field"),
                        [
                            PredefinedFn.keyword_assignment(
                                "default_factory",
                                expr.ExprIdent(prop.default_factory.pyfunc),
                            )
                        ],
                    )

                cls_ast(
                    stmt.DefClassVarStatement(
                        prop.name, pytype.type, prop_default_value
                    )
                )
            elif isinstance(prop, ObjectProperty):
                if prop.target.db is not None:
                    # if the target class is in the database, we expect the user to pass the foreign key for it.
                    pytype = (
                        assert_not_null(prop.target.get_id_property())
                        .get_data_model_datatype()
                        .get_python_type()
                    )
                else:
                    pytype = PyTypeWithDep(
                        f"Update{prop.target.name}",
                        [
                            f"{target_pkg.module(prop.target.get_pymodule_name()).path}.Update{prop.target.name}"
                        ],
                    )

                if prop.cardinality.is_star_to_many():
                    pytype = pytype.as_list_type()
                elif prop.is_optional:
                    pytype = pytype.as_optional_type()

                for dep in pytype.deps:
                    program.import_(dep, True)

                cls_ast(stmt.DefClassVarStatement(prop.name, pytype.type))

        if is_on_update_value_updated:
            program.import_("typing.Optional", True)
            program.import_("sera.typing.is_set", True)
            cls_ast(
                stmt.Comment(
                    "A marker to indicate that the system-controlled properties are updated"
                ),
                stmt.DefClassVarStatement(
                    "_is_scp_updated", "bool", expr.ExprConstant(False)
                ),
                stmt.LineBreak(),
                lambda ast: ast.func(
                    "__post_init__",
                    [
                        DeferredVar.simple("self"),
                    ],
                )(
                    stmt.AssignStatement(
                        PredefinedFn.attr_getter(
                            expr.ExprIdent("self"), expr.ExprIdent("_is_scp_updated")
                        ),
                        expr.ExprConstant(False),
                    ),
                ),
                stmt.LineBreak(),
                lambda ast: make_uscp_func(cls, "update", ast, ident_manager),
            )

        cls_ast(
            stmt.LineBreak(),
            lambda ast00: ast00.func(
                "to_db",
                [
                    DeferredVar.simple("self"),
                ],
                return_type=expr.ExprIdent(
                    f"{cls.name}DB" if cls.db is not None else cls.name
                ),
            )(
                (
                    stmt.AssertionStatement(
                        expr.ExprLogicalAnd(
                            [
                                expr.ExprFuncCall(
                                    expr.ExprIdent("is_set"),
                                    [
                                        PredefinedFn.attr_getter(
                                            expr.ExprIdent("self"),
                                            expr.ExprIdent(prop.name),
                                        )
                                    ],
                                )
                                for prop in cls.properties.values()
                                if prop.data.system_controlled is not None
                                and prop.data.system_controlled.is_on_update_value_updated()
                            ]
                        ),
                        expr.ExprConstant(
                            "The model data must be verified before converting to db model"
                        ),
                    )
                    if is_on_update_value_updated
                    else None
                ),
                lambda ast10: ast10.return_(
                    expr.ExprFuncCall(
                        expr.ExprIdent(
                            f"{cls.name}DB" if cls.db is not None else cls.name
                        ),
                        [
                            (
                                ident_manager.use("UNSET")
                                if prop.data.system_controlled is not None
                                and prop.data.system_controlled.is_on_update_ignored()
                                else to_db_type_conversion(
                                    program, expr.ExprIdent("self"), cls, "update", prop
                                )
                            )
                            for prop in cls.properties.values()
                        ],
                    )
                ),
            ),
        )

    def make_normal(program: Program, cls: Class):
        if not cls.is_public:
            # skip classes that are not public
            return

        program.import_("__future__.annotations", True)
        program.import_("msgspec", False)
        if cls.db is not None:
            # if the class is stored in the database, we need to import the database module
            program.import_(
                app.models.db.path + f".{cls.get_pymodule_name()}.{cls.name}",
                True,
                alias=f"{cls.name}DB",
            )

        cls_ast = program.root.class_(cls.name, [expr.ExprIdent("msgspec.Struct")])
        for prop in cls.properties.values():
            if prop.data.is_private:
                # skip private fields as this is for APIs exchange
                continue

            if isinstance(prop, DataProperty):
                pytype = prop.get_data_model_datatype().get_python_type()
                if prop.is_optional:
                    pytype = pytype.as_optional_type()

                for dep in pytype.deps:
                    program.import_(dep, True)

                cls_ast(stmt.DefClassVarStatement(prop.name, pytype.type))
            elif isinstance(prop, ObjectProperty):
                if prop.target.db is not None:
                    pytype = (
                        assert_not_null(prop.target.get_id_property())
                        .get_data_model_datatype()
                        .get_python_type()
                    )
                else:
                    pytype = PyTypeWithDep(
                        prop.target.name,
                        [
                            f"{target_pkg.module(prop.target.get_pymodule_name()).path}.{prop.target.name}"
                        ],
                    )

                if prop.cardinality.is_star_to_many():
                    pytype = pytype.as_list_type()
                elif prop.is_optional:
                    pytype = pytype.as_optional_type()

                for dep in pytype.deps:
                    program.import_(dep, True)

                cls_ast(stmt.DefClassVarStatement(prop.name, pytype.type))

        cls_ast(
            stmt.LineBreak(),
            (
                stmt.PythonDecoratorStatement(
                    expr.ExprFuncCall(expr.ExprIdent("classmethod"), [])
                )
                if cls.db is not None
                else None
            ),
            lambda ast00: (
                ast00.func(
                    "from_db",
                    [
                        DeferredVar.simple("cls"),
                        DeferredVar.simple("record", expr.ExprIdent(f"{cls.name}DB")),
                    ],
                )(
                    lambda ast10: ast10.return_(
                        expr.ExprFuncCall(
                            expr.ExprIdent("cls"),
                            [
                                from_db_type_conversion(expr.ExprIdent("record"), prop)
                                for prop in cls.properties.values()
                                if not prop.data.is_private
                            ],
                        )
                    )
                )
                if cls.db is not None
                else None
            ),
        )

        if cls.db is None:
            as_composite_args = [DeferredVar.simple("cls")]
            as_composite_null_condition = []
            for prop in cls.properties.values():
                assert (
                    not prop.data.is_private
                ), f"Embedded classes should not have private properties: {cls.name}.{prop.name}"
                as_composite_args.append(DeferredVar.simple(prop.name))
                as_composite_null_condition.append(
                    expr.ExprIs(expr.ExprIdent(prop.name), expr.ExprConstant(None))
                )

            # For simplicity, we assume that this embedded class can be used in a nullable field (check if all properties are None and return None).
            # However, we could be more efficient by checking if there are any other classes that use this class as a composite and are non-optional,
            # and eliminate the None check because we know that the class will always be re-created.
            cls_ast(
                stmt.LineBreak(),
                stmt.PythonDecoratorStatement(
                    expr.ExprFuncCall(expr.ExprIdent("classmethod"), [])
                ),
                lambda ast: ast.func(
                    "as_composite",
                    vars=as_composite_args,
                    return_type=expr.ExprIdent(f"Optional[{cls.name}]"),
                    comment="Create an embedded instance from the embedded columns in the database table. If all properties of this embedded class are None (indicating that the parent field is None), then this function will return None.",
                )(
                    lambda ast_l1: ast_l1.if_(
                        expr.ExprLogicalAnd(as_composite_null_condition)
                    )(lambda ast_l2: ast_l2.return_(expr.ExprConstant(None))),
                    lambda ast_l1: ast_l1.return_(
                        expr.ExprFuncCall(
                            expr.ExprIdent("cls"),
                            [
                                from_db_type_conversion(
                                    expr.ExprIdent(""), prop, expr.ExprIdent(prop.name)
                                )
                                for prop in cls.properties.values()
                            ],
                        )
                    ),
                ),
                stmt.LineBreak(),
                lambda ast: ast.func(
                    "__composite_values__",
                    [
                        DeferredVar.simple("self"),
                    ],
                    return_type=expr.ExprIdent("tuple"),
                    comment="Return the values of the properties of this embedded class as a tuple. This is used to create a composite object in SQLAlchemy.",
                )(
                    lambda ast_l1: ast_l1.return_(
                        PredefinedFn.tuple(
                            [
                                to_db_type_conversion(
                                    program, expr.ExprIdent("self"), cls, "create", prop
                                )
                                for prop in cls.properties.values()
                            ]
                        )
                    )
                ),
            )

    for cls in schema.topological_sort():
        if cls.name in reference_classes:
            continue

        program = Program()
        make_create(program, cls)
        program.root.linebreak()
        make_update(program, cls)
        program.root.linebreak()
        make_normal(program, cls)
        target_pkg.module(cls.get_pymodule_name()).write(program)


def make_python_relational_model(
    schema: Schema,
    target_pkg: Package,
    target_data_pkg: Package,
    reference_classes: dict[str, ObjectPath],
):
    """Make python classes for relational database using SQLAlchemy.

    The new classes is going be compatible with SQLAlchemy 2.

    Args:
        schema: The schema to generate the classes from.
        target_pkg: The package to write the classes to.
        target_data_pkg: The package to write the data classes to.
        reference_classes: A dictionary of class names to their references (e.g., the ones that are defined outside and used as referenced such as Tenant).
    """
    app = target_pkg.app

    def get_property_name(prop: DataProperty | ObjectProperty):
        if isinstance(prop, ObjectProperty):
            if prop.target.db is not None:
                return f"{prop.name}_id"
        return prop.name

    def make_base(custom_types: Sequence[ObjectProperty]):
        """Make a base class for our database."""
        program = Program()
        program.import_("__future__.annotations", True)
        program.import_("sera.libs.base_orm.BaseORM", True)
        program.import_("sera.libs.base_orm.create_engine", True)
        program.import_("sera.libs.base_orm.create_async_engine", True)
        program.import_("sqlalchemy.orm.DeclarativeBase", True)
        program.import_("sqlalchemy.orm.Session", True)
        program.import_("sqlalchemy.ext.asyncio.AsyncSession", True)
        program.import_("sqlalchemy.text", True)

        # assume configuration for the app at the top level
        program.import_(f"{app.config.path}.DB_CONNECTION", True)
        program.import_(f"{app.config.path}.DB_DEBUG", True)
        program.import_(f"contextlib.contextmanager", True)

        program.root.linebreak()

        type_map = []
        for custom_type in custom_types:
            program.import_(
                f"{target_data_pkg.module(custom_type.target.get_pymodule_name()).path}.{custom_type.target.name}",
                is_import_attr=True,
            )

            if custom_type.cardinality.is_star_to_many():
                if custom_type.is_map:
                    program.import_("sera.libs.base_orm.DictDataclassType", True)
                    type = f"dict[str, {custom_type.target.name}]"
                    maptype = f"DictDataclassType({custom_type.target.name})"
                else:
                    program.import_("sera.libs.base_orm.ListDataclassType", True)
                    type = f"list[{custom_type.target.name}]"
                    maptype = f"ListDataclassType({custom_type.target.name})"
            else:
                program.import_("sera.libs.base_orm.DataclassType", True)
                type = custom_type.target.name
                maptype = f"DataclassType({custom_type.target.name})"

            if custom_type.is_optional:
                program.import_("typing.Optional", True)
                type = f"Optional[{type}]"

            type_map.append((expr.ExprIdent(type), expr.ExprIdent(maptype)))

        program.root.class_(
            "Base", [expr.ExprIdent("DeclarativeBase"), expr.ExprIdent("BaseORM")]
        )(
            stmt.DefClassVarStatement(
                "type_annotation_map", "dict", PredefinedFn.dict(type_map)
            ),
            return_self=True,
        )

        program.root.linebreak()
        program.root.assign(
            DeferredVar.simple("engine"),
            expr.ExprFuncCall(
                expr.ExprIdent("create_engine"),
                [
                    expr.ExprIdent("DB_CONNECTION"),
                    PredefinedFn.keyword_assignment("echo", expr.ExprIdent("DB_DEBUG")),
                ],
            ),
        )
        program.root.assign(
            DeferredVar.simple("async_engine"),
            expr.ExprFuncCall(
                expr.ExprIdent("create_async_engine"),
                [
                    expr.ExprIdent("DB_CONNECTION"),
                    PredefinedFn.keyword_assignment("echo", expr.ExprIdent("DB_DEBUG")),
                ],
            ),
        )

        program.root.linebreak()
        program.root.func("create_db_and_tables", [])(
            stmt.PythonStatement("Base.metadata.create_all(engine)"),
        )

        program.root.linebreak()
        program.root.func("get_async_session", [], is_async=True)(
            lambda ast: ast.python_stmt(
                "async with AsyncSession(async_engine, expire_on_commit=False) as session:"
            )(
                lambda ast_l1: ast_l1.try_()(stmt.PythonStatement("yield session")),
                lambda ast_l1: ast_l1.catch()(
                    stmt.SingleExprStatement(
                        expr.ExprAwait(
                            expr.ExprFuncCall(
                                PredefinedFn.attr_getter(
                                    expr.ExprIdent("session"),
                                    expr.ExprIdent("rollback"),
                                ),
                                [],
                            )
                        )
                    ),
                    stmt.PythonStatement("raise"),
                ),
                lambda ast_l1: ast_l1.else_()(
                    stmt.SingleExprStatement(
                        expr.ExprAwait(
                            expr.ExprFuncCall(
                                PredefinedFn.attr_getter(
                                    expr.ExprIdent("session"), expr.ExprIdent("execute")
                                ),
                                [
                                    expr.ExprFuncCall(
                                        expr.ExprIdent("text"),
                                        [expr.ExprConstant("RESET ROLE;")],
                                    )
                                ],
                            )
                        )
                    ),
                    stmt.SingleExprStatement(
                        expr.ExprAwait(
                            expr.ExprFuncCall(
                                PredefinedFn.attr_getter(
                                    expr.ExprIdent("session"), expr.ExprIdent("commit")
                                ),
                                [],
                            )
                        )
                    ),
                ),
            )
        )

        program.root.linebreak()
        program.root.python_stmt("@contextmanager")
        program.root.func("get_session", [])(
            lambda ast: ast.python_stmt(
                "with Session(engine, expire_on_commit=False) as session:"
            )(
                lambda ast_l1: ast_l1.try_()(stmt.PythonStatement("yield session")),
                lambda ast_l1: ast_l1.catch()(
                    stmt.SingleExprStatement(
                        expr.ExprFuncCall(
                            PredefinedFn.attr_getter(
                                expr.ExprIdent("session"), expr.ExprIdent("rollback")
                            ),
                            [],
                        )
                    ),
                    stmt.PythonStatement("raise"),
                ),
                lambda ast_l1: ast_l1.else_()(
                    stmt.SingleExprStatement(
                        expr.ExprFuncCall(
                            PredefinedFn.attr_getter(
                                expr.ExprIdent("session"), expr.ExprIdent("execute")
                            ),
                            [
                                expr.ExprFuncCall(
                                    expr.ExprIdent("text"),
                                    [expr.ExprConstant("RESET ROLE;")],
                                )
                            ],
                        )
                    ),
                    stmt.SingleExprStatement(
                        expr.ExprFuncCall(
                            PredefinedFn.attr_getter(
                                expr.ExprIdent("session"), expr.ExprIdent("commit")
                            ),
                            [],
                        )
                    ),
                ),
            )
        )

        target_pkg.module("base").write(program)

    def make_orm(cls: Class):
        if cls.db is None or cls.name in reference_classes:
            # skip classes that are not stored in the database
            return

        program = Program()
        program.import_("__future__.annotations", True)
        program.import_("sqlalchemy.orm.MappedAsDataclass", True)
        program.import_("sqlalchemy.orm.mapped_column", True)
        program.import_("sqlalchemy.orm.Mapped", True)
        program.import_(f"{target_pkg.path}.base.Base", True)

        ident_manager = ImportHelper(
            program,
            GLOBAL_IDENTS,
        )

        index_stmts = []
        if len(cls.db.indices) > 0:
            program.import_("sqlalchemy.Index", True)
            index_stmts.append(
                stmt.DefClassVarStatement(
                    "_table_args__",
                    None,
                    PredefinedFn.tuple(
                        [
                            expr.ExprFuncCall(
                                expr.ExprIdent("Index"),
                                [expr.ExprConstant(index.name)]
                                + [
                                    expr.ExprConstant(
                                        get_property_name(cls.properties[prop])
                                    )
                                    for prop in index.columns
                                ]
                                + (
                                    [
                                        PredefinedFn.keyword_assignment(
                                            "unique", expr.ExprConstant(index.unique)
                                        )
                                    ]
                                    if index.unique
                                    else []
                                ),
                            )
                            for index in cls.db.indices
                        ]
                    ),
                )
            )

        cls_ast = program.root.class_(
            cls.name, [expr.ExprIdent("MappedAsDataclass"), expr.ExprIdent("Base")]
        )
        cls_ast(
            stmt.DefClassVarStatement(
                "__tablename__",
                type=None,
                value=expr.ExprConstant(cls.db.table_name),
            ),
            *index_stmts,
            stmt.LineBreak(),
        )

        for prop in cls.properties.values():
            if prop.db is None:
                # skip properties that are not stored in the database
                continue

            if isinstance(prop, DataProperty):
                sqltype = prop.datatype.get_sqlalchemy_type()
                for dep in sqltype.deps:
                    program.import_(dep, True)

                propname = prop.name

                if prop.is_optional:
                    program.import_("typing.Optional", True)
                    proptype = f"Mapped[Optional[{sqltype.mapped_pytype}]]"
                else:
                    proptype = f"Mapped[{sqltype.mapped_pytype}]"

                propvalargs: list[expr.Expr] = [expr.ExprIdent(sqltype.type)]
                if prop.db.foreign_key is not None:
                    assert (
                        prop.db.foreign_key.db is not None
                    ), f"Foreign key {prop.db.foreign_key.name} must have a database mapping"
                    foreign_key_idprop = prop.db.foreign_key.get_id_property()
                    assert (
                        foreign_key_idprop is not None
                    ), f"Foreign key {prop.db.foreign_key.name} must have an id property"
                    propvalargs.append(
                        expr.ExprFuncCall(
                            ident_manager.use("ForeignKey"),
                            [
                                expr.ExprConstant(
                                    f"{prop.db.foreign_key.db.table_name}.{foreign_key_idprop.name}"
                                ),
                                PredefinedFn.keyword_assignment(
                                    "ondelete",
                                    expr.ExprConstant("CASCADE"),
                                ),
                                PredefinedFn.keyword_assignment(
                                    "onupdate",
                                    expr.ExprConstant("CASCADE"),
                                ),
                            ],
                        )
                    )
                if prop.db.is_primary_key:
                    propvalargs.append(
                        PredefinedFn.keyword_assignment(
                            "primary_key", expr.ExprConstant(True)
                        )
                    )
                    if prop.db.is_auto_increment:
                        propvalargs.append(
                            PredefinedFn.keyword_assignment(
                                "autoincrement", expr.ExprConstant("auto")
                            )
                        )
                else:
                    if prop.db.is_unique:
                        propvalargs.append(
                            PredefinedFn.keyword_assignment(
                                "unique", expr.ExprConstant(True)
                            )
                        )
                    elif prop.db.is_indexed:
                        propvalargs.append(
                            PredefinedFn.keyword_assignment(
                                "index", expr.ExprConstant(True)
                            )
                        )
                if prop.is_optional:
                    propvalargs.append(
                        PredefinedFn.keyword_assignment(
                            "nullable", expr.ExprConstant(True)
                        )
                    )
                propval = expr.ExprFuncCall(
                    expr.ExprIdent("mapped_column"), propvalargs
                )
                cls_ast(stmt.DefClassVarStatement(propname, proptype, propval))
            else:
                assert isinstance(prop, ObjectProperty)
                make_python_relational_object_property(
                    program=program,
                    target_pkg=target_pkg,
                    target_data_pkg=target_data_pkg,
                    cls_ast=cls_ast,
                    cls=cls,
                    prop=prop,
                    custom_types=custom_types,
                )

        target_pkg.module(cls.get_pymodule_name()).write(program)

    custom_types: list[ObjectProperty] = []

    for cls in schema.topological_sort():
        make_orm(cls)

    # make a base class that implements the mapping for custom types
    custom_types = filter_duplication(
        custom_types, lambda p: (p.target.name, p.cardinality, p.is_optional, p.is_map)
    )
    make_base(custom_types)


def make_python_relational_object_property(
    program: Program,
    target_pkg: Package,
    target_data_pkg: Package,
    cls_ast: AST,
    cls: Class,
    prop: ObjectProperty,
    custom_types: list[ObjectProperty],
):
    assert prop.db is not None
    if prop.target.db is not None:
        # if the target class is in the database, we generate a foreign key for it.
        program.import_("sqlalchemy.ForeignKey", True)

        if prop.cardinality == Cardinality.MANY_TO_MANY:
            make_python_relational_object_property_many_to_many(
                program, cls_ast, target_pkg, cls, prop
            )
            return

        if prop.cardinality.is_star_to_many():
            raise NotImplementedError((cls.name, prop.name))

        # we store this class in the database
        propname = f"{prop.name}_id"
        idprop = prop.target.get_id_property()
        assert idprop is not None
        idprop_pytype = idprop.datatype.get_sqlalchemy_type()
        for dep in idprop_pytype.deps:
            program.import_(dep, True)

        proptype = f"Mapped[{idprop_pytype.mapped_pytype}]"
        propval = expr.ExprFuncCall(
            expr.ExprIdent("mapped_column"),
            [
                expr.ExprIdent(idprop_pytype.type),
                expr.ExprFuncCall(
                    expr.ExprIdent("ForeignKey"),
                    [
                        expr.ExprConstant(f"{prop.target.db.table_name}.{idprop.name}"),
                        PredefinedFn.keyword_assignment(
                            "ondelete",
                            expr.ExprConstant(prop.db.on_target_delete.to_sqlalchemy()),
                        ),
                        PredefinedFn.keyword_assignment(
                            "onupdate",
                            expr.ExprConstant(prop.db.on_target_update.to_sqlalchemy()),
                        ),
                    ],
                ),
                PredefinedFn.keyword_assignment(
                    "nullable",
                    expr.ExprConstant(prop.is_optional),
                ),
            ],
        )

        cls_ast(stmt.DefClassVarStatement(propname, proptype, propval))
        return

    # if the target class is not in the database,
    program.import_(
        f"{target_data_pkg.module(prop.target.get_pymodule_name()).path}.{prop.target.name}",
        is_import_attr=True,
    )
    propname = prop.name
    if prop.cardinality.is_star_to_many():
        if prop.is_map:
            proptype = f"Mapped[dict[str, {prop.target.name}]]"
        else:
            proptype = f"Mapped[list[{prop.target.name}]]"
    else:
        proptype = f"Mapped[{prop.target.name}]"

    # we have two choices, one is to create a composite class, one is to create a custom field
    if prop.db.is_embedded == "composite":
        # for a class to be composite, it must have only data properties
        program.import_("sqlalchemy.orm.composite", True)
        propvalargs: list[expr.Expr] = [expr.ExprIdent(prop.target.name)]
        for p in prop.target.properties.values():
            propvalargs.append(
                expr.ExprFuncCall(
                    expr.ExprIdent("mapped_column"),
                    [
                        expr.ExprConstant(f"{prop.name}_{p.name}"),
                        expr.ExprIdent(
                            assert_isinstance(p, DataProperty)
                            .datatype.get_sqlalchemy_type()
                            .type
                        ),
                        PredefinedFn.keyword_assignment(
                            "nullable",
                            expr.ExprConstant(prop.is_optional or p.is_optional),
                        ),
                    ],
                )
            )
        propval = expr.ExprFuncCall(
            expr.ExprIdent("composite"),
            propvalargs,
        )
    else:
        assert prop.db.is_embedded == "json"
        # we create a custom field, the custom field mapping need to be defined in the base
        propval = expr.ExprFuncCall(
            expr.ExprIdent("mapped_column"),
            [
                PredefinedFn.keyword_assignment(
                    "nullable",
                    expr.ExprConstant(prop.is_optional),
                ),
            ],
        )
        custom_types.append(prop)

    cls_ast(stmt.DefClassVarStatement(propname, proptype, propval))


def make_python_relational_object_property_many_to_many(
    program: Program, ast: AST, target_pkg: Package, cls: Class, prop: ObjectProperty
):
    assert cls.db is not None
    assert prop.db is not None and prop.target.db is not None
    assert prop.cardinality == Cardinality.MANY_TO_MANY

    # we create a new table to store the many-to-many relationship
    new_table = f"{cls.name}{prop.target.name}"
    clsdb = cls.db
    propdb = prop.db
    targetdb = prop.target.db

    source_idprop = assert_not_null(cls.get_id_property())
    source_id_type = source_idprop.datatype.get_python_type().type
    target_idprop = assert_not_null(prop.target.get_id_property())
    target_id_type = target_idprop.datatype.get_python_type().type

    newprogram = Program()
    newprogram.import_("__future__.annotations", True)
    newprogram.import_("sqlalchemy.ForeignKey", True)
    newprogram.import_("sqlalchemy.orm.mapped_column", True)
    newprogram.import_("sqlalchemy.orm.Mapped", True)
    newprogram.import_("sqlalchemy.orm.relationship", True)
    newprogram.import_(f"{target_pkg.path}.base.Base", True)
    newprogram.import_("typing.TYPE_CHECKING", True)
    newprogram.import_area.if_(expr.ExprIdent("TYPE_CHECKING"))(
        lambda ast00: ast00.import_(
            target_pkg.path + f".{cls.get_pymodule_name()}.{cls.name}",
            is_import_attr=True,
        ),
        lambda ast10: ast10.import_(
            target_pkg.path + f".{prop.target.get_pymodule_name()}.{prop.target.name}",
            is_import_attr=True,
        ),
    )

    newprogram.root(
        stmt.LineBreak(),
        lambda ast00: ast00.class_(new_table, [expr.ExprIdent("Base")])(
            stmt.DefClassVarStatement(
                "__tablename__",
                type=None,
                value=expr.ExprConstant(f"{clsdb.table_name}_{targetdb.table_name}"),
            ),
            stmt.LineBreak(),
            stmt.DefClassVarStatement(
                to_snake_case(cls.name),
                f"Mapped[{cls.name}]",
                expr.ExprFuncCall(
                    expr.ExprIdent("relationship"),
                    [
                        PredefinedFn.keyword_assignment(
                            "back_populates",
                            expr.ExprConstant(prop.name),
                        ),
                        PredefinedFn.keyword_assignment(
                            "lazy",
                            expr.ExprConstant("raise_on_sql"),
                        ),
                    ],
                ),
            ),
            stmt.DefClassVarStatement(
                to_snake_case(cls.name) + "_id",
                f"Mapped[{source_id_type}]",
                expr.ExprFuncCall(
                    expr.ExprIdent("mapped_column"),
                    [
                        expr.ExprFuncCall(
                            expr.ExprIdent("ForeignKey"),
                            [
                                expr.ExprConstant(
                                    f"{clsdb.table_name}.{source_idprop.name}"
                                ),
                                PredefinedFn.keyword_assignment(
                                    "ondelete",
                                    expr.ExprConstant(
                                        propdb.on_source_delete.to_sqlalchemy()
                                    ),
                                ),
                                PredefinedFn.keyword_assignment(
                                    "onupdate",
                                    expr.ExprConstant(
                                        propdb.on_source_update.to_sqlalchemy()
                                    ),
                                ),
                            ],
                        ),
                        PredefinedFn.keyword_assignment(
                            "primary_key", expr.ExprConstant(True)
                        ),
                    ],
                ),
            ),
            stmt.DefClassVarStatement(
                to_snake_case(prop.target.name),
                f"Mapped[{prop.target.name}]",
                expr.ExprFuncCall(
                    expr.ExprIdent("relationship"),
                    [
                        PredefinedFn.keyword_assignment(
                            "lazy",
                            expr.ExprConstant("raise_on_sql"),
                        ),
                    ],
                ),
            ),
            stmt.DefClassVarStatement(
                to_snake_case(prop.target.name) + "_id",
                f"Mapped[{target_id_type}]",
                expr.ExprFuncCall(
                    expr.ExprIdent("mapped_column"),
                    [
                        expr.ExprFuncCall(
                            expr.ExprIdent("ForeignKey"),
                            [
                                expr.ExprConstant(
                                    f"{targetdb.table_name}.{target_idprop.name}"
                                ),
                                PredefinedFn.keyword_assignment(
                                    "ondelete",
                                    expr.ExprConstant(
                                        propdb.on_target_delete.to_sqlalchemy()
                                    ),
                                ),
                                PredefinedFn.keyword_assignment(
                                    "onupdate",
                                    expr.ExprConstant(
                                        propdb.on_target_update.to_sqlalchemy()
                                    ),
                                ),
                            ],
                        ),
                        PredefinedFn.keyword_assignment(
                            "primary_key", expr.ExprConstant(True)
                        ),
                    ],
                ),
            ),
        ),
    )

    new_table_module = target_pkg.module(to_snake_case(new_table))
    new_table_module.write(newprogram)

    # now we add the relationship to the source.
    # we can configure it to be list, set, or dict depends on what we want.
    program.import_(new_table_module.path + f".{new_table}", True)
    program.import_("sqlalchemy.orm.relationship", True)

    # program.import_("typing.TYPE_CHECKING", True)
    # program.import_area.if_(expr.ExprIdent("TYPE_CHECKING"))(
    #     lambda ast00: ast00.import_(
    #         target_pkg.path + f".{prop.target.get_pymodule_name()}.{prop.target.name}",
    #         is_import_attr=True,
    #     )
    # )

    ast(
        stmt.DefClassVarStatement(
            prop.name,
            f"Mapped[list[{new_table}]]",
            expr.ExprFuncCall(
                expr.ExprIdent("relationship"),
                [
                    PredefinedFn.keyword_assignment(
                        "back_populates",
                        expr.ExprConstant(to_snake_case(cls.name)),
                    ),
                    PredefinedFn.keyword_assignment(
                        "lazy",
                        expr.ExprConstant("raise_on_sql"),
                    ),
                ],
            ),
        ),
    )


def get_data_conversion(
    source_pytype: str, target_pytype: str
) -> Callable[[expr.Expr], expr.Expr]:
    if source_pytype == target_pytype:
        return lambda x: x
    if source_pytype == "str" and target_pytype == "bytes":
        return lambda x: expr.ExprMethodCall(x, "encode", [])
    raise NotImplementedError(f"Cannot convert {source_pytype} to {target_pytype}")
