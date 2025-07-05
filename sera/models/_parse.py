from __future__ import annotations

import re
from copy import deepcopy
from pathlib import Path
from typing import Sequence

import orjson
import serde.yaml

from sera.models._class import Class, ClassDBMapInfo, Index
from sera.models._constraints import Constraint, predefined_constraints
from sera.models._datatype import (
    DataType,
    PyTypeWithDep,
    SQLTypeWithDep,
    TsTypeWithDep,
    predefined_datatypes,
    predefined_py_datatypes,
    predefined_sql_datatypes,
    predefined_ts_datatypes,
)
from sera.models._default import DefaultFactory
from sera.models._enum import Enum, EnumValue
from sera.models._multi_lingual_string import MultiLingualString
from sera.models._property import (
    Cardinality,
    DataPropDBInfo,
    DataProperty,
    ForeignKeyOnDelete,
    ForeignKeyOnUpdate,
    GetSCPropValueFunc,
    ObjectPropDBInfo,
    ObjectProperty,
    PropDataAttrs,
    SystemControlledAttrs,
)
from sera.models._schema import Schema
from sera.typing import UNSET


def parse_schema(name: str, files: Sequence[Path | str]) -> Schema:
    schema = Schema(name=name, classes={}, enums={})

    # parse all classes
    raw_defs = {}
    for file in files:
        for k, v in serde.yaml.deser(file).items():
            if k.startswith("enum:"):
                schema.enums[k[5:]] = _parse_enum(schema, k[5:], v)
                continue
            cdef = _parse_class_without_prop(schema, k, v)
            assert k not in schema.classes
            schema.classes[k] = cdef
            raw_defs[k] = v

    # now parse properties of the classes
    for clsname, v in raw_defs.items():
        cdef = schema.classes[clsname]
        for propname, prop in (v["props"] or {}).items():
            assert propname not in cdef.properties
            cdef.properties[propname] = _parse_property(schema, propname, prop)

    return schema


def _parse_class_without_prop(schema: Schema, clsname: str, cls: dict) -> Class:
    db = None
    if "db" in cls:
        indices = []
        for idx in cls["db"].get("indices", []):
            index = Index(
                name=idx.get("name", "_".join(idx["columns"]) + "_index"),
                columns=idx["columns"],
                unique=idx.get("unique", False),
            )
            indices.append(index)
        db = ClassDBMapInfo(table_name=cls["db"]["table_name"], indices=indices)

    return Class(
        name=clsname,
        label=_parse_multi_lingual_string(cls["label"]),
        description=_parse_multi_lingual_string(cls.get("desc", "")),
        properties={},
        db=db,
    )


def _parse_enum(schema: Schema, enum_name: str, enum: dict) -> Enum:
    values = {}
    for k, v in enum.items():
        if isinstance(v, (str, int)):
            values[k] = EnumValue(
                name=k, value=v, description=MultiLingualString.en("")
            )
        else:
            try:
                values[k] = EnumValue(
                    name=k,
                    value=v["value"],
                    description=_parse_multi_lingual_string(v.get("desc", "")),
                )
            except KeyError as e:
                raise ValueError(f"Invalid enum value definition for {k}: {v}") from e
    return Enum(name=enum_name, values=values)


def _parse_property(
    schema: Schema, prop_name: str, prop: dict
) -> DataProperty | ObjectProperty:
    if isinstance(prop, str):
        # deprecated
        assert False, prop
        # datatype = prop
        # if datatype in schema.classes:
        #     return ObjectProperty(
        #         name=prop_name,
        #         label=_parse_multi_lingual_string(prop_name),
        #         description=_parse_multi_lingual_string(""),
        #         target=schema.classes[datatype],
        #         cardinality=Cardinality.ONE_TO_ONE,
        #     )
        # else:
        #     return DataProperty(
        #         name=prop_name,
        #         label=_parse_multi_lingual_string(prop_name),
        #         description=_parse_multi_lingual_string(""),
        #         datatype=_parse_datatype(schema, datatype),
        #     )

    db = prop.get("db", {})
    _data = prop.get("data", {})
    data_attrs = PropDataAttrs(
        is_private=_data.get("is_private", False),
        datatype=(
            _parse_datatype(schema, _data["datatype"]) if "datatype" in _data else None
        ),
        constraints=[
            _parse_constraint(constraint) for constraint in _data.get("constraints", [])
        ],
        system_controlled=_parse_system_controlled_attrs(
            _data.get("system_controlled")
        ),
        default_value=UNSET if "default_value" not in _data else _data["default_value"],
    )

    assert isinstance(prop, dict), prop
    if "datatype" in prop:
        return DataProperty(
            name=prop_name,
            label=_parse_multi_lingual_string(prop.get("label", prop_name)),
            description=_parse_multi_lingual_string(prop.get("desc", "")),
            datatype=_parse_datatype(schema, prop["datatype"]),
            data=data_attrs,
            db=(
                DataPropDBInfo(
                    is_primary_key=db.get("is_primary_key", False),
                    is_auto_increment=db.get("is_auto_increment", False),
                    is_unique=db.get("is_unique", False),
                    is_indexed=db.get("is_indexed", False)
                    or db.get("is_unique", False)
                    or db.get("is_primary_key", False),
                    foreign_key=schema.classes.get(db.get("foreign_key")),
                )
                if "db" in prop
                else None
            ),
            is_optional=prop.get("is_optional", False),
            default_value=_parse_default_value(prop.get("default_value", None)),
            default_factory=_parse_default_factory(prop.get("default_factory", None)),
        )

    assert "target" in prop, prop
    return ObjectProperty(
        name=prop_name,
        label=_parse_multi_lingual_string(prop.get("label", prop_name)),
        description=_parse_multi_lingual_string(prop.get("desc", "")),
        target=schema.classes[prop["target"]],
        cardinality=Cardinality(prop.get("cardinality", "1:1")),
        is_optional=prop.get("is_optional", False),
        data=data_attrs,
        db=(
            ObjectPropDBInfo(
                is_embedded=db.get("is_embedded", None),
                on_target_delete=ForeignKeyOnDelete(
                    db.get("on_target_delete", "restrict")
                ),
                on_target_update=ForeignKeyOnUpdate(
                    db.get("on_target_update", "restrict")
                ),
                on_source_delete=ForeignKeyOnDelete(
                    db.get("on_source_delete", "restrict")
                ),
                on_source_update=ForeignKeyOnUpdate(
                    db.get("on_source_update", "restrict")
                ),
            )
            if "db" in prop
            else None
        ),
    )


def _parse_multi_lingual_string(o: dict | str) -> MultiLingualString:
    if isinstance(o, str):
        return MultiLingualString.en(o)
    assert isinstance(o, dict), o
    assert "en" in o
    return MultiLingualString(lang2value=o, lang="en")


def _parse_constraint(constraint: str) -> Constraint:
    if constraint not in predefined_constraints:
        raise NotImplementedError(constraint)
    return predefined_constraints[constraint]


def _parse_datatype(schema: Schema, datatype: dict | str) -> DataType:
    if isinstance(datatype, str):
        if datatype.endswith("[]"):
            datatype = datatype[:-2]
            is_list = True
        else:
            is_list = False

        if datatype.startswith("enum:"):
            enum_name = datatype[5:]
            if enum_name not in schema.enums:
                raise NotImplementedError("Unknown enum: " + enum_name)
            enum = schema.enums[enum_name]
            return DataType(
                # we can't set the correct dependency of this enum type because we do not know
                # the correct package yet.
                pytype=PyTypeWithDep(
                    type=enum.name,
                    deps=[
                        f"{schema.name}.models.enums.{enum.get_pymodule_name()}.{enum.name}"
                    ],
                ),
                sqltype=SQLTypeWithDep(
                    type="String", mapped_pytype="str", deps=["sqlalchemy.String"]
                ),
                tstype=TsTypeWithDep(
                    type=enum.name, deps=[f"@.models.enums.{enum.name}"]
                ),
                is_list=is_list,
            )

        if datatype not in predefined_datatypes:
            raise NotImplementedError(datatype)

        dt = deepcopy(predefined_datatypes[datatype])
        dt.is_list = is_list
        return dt
    if isinstance(datatype, dict):
        is_list = datatype.get("is_list", False)

        # Parse SQL type and argument if present
        m = re.match(r"^([a-zA-Z0-9_]+)(\([^)]+\))?$", datatype["sqltype"])
        if m is not None:
            sql_type_name = m.group(1)
            sql_type_arg = m.group(2)
            # Use the extracted type to get the predefined SQL type
            if sql_type_name not in predefined_sql_datatypes:
                raise NotImplementedError(sql_type_name)
            sql_type = predefined_sql_datatypes[sql_type_name]
            if sql_type_arg is not None:
                # process the argument
                sql_type.type = sql_type.type + sql_type_arg
        else:
            raise ValueError(f"Invalid SQL type format: {datatype['sqltype']}")

        return DataType(
            pytype=predefined_py_datatypes[datatype["pytype"]],
            sqltype=sql_type,
            tstype=predefined_ts_datatypes[datatype["tstype"]],
            is_list=is_list,
        )

    raise NotImplementedError(datatype)


def _parse_default_value(
    default_value: str | int | bool | None,
) -> str | int | bool | None:
    if default_value is None:
        return None
    if not isinstance(default_value, (str, int, bool)):
        raise NotImplementedError(default_value)
    return default_value


def _parse_default_factory(default_factory: dict | None) -> DefaultFactory | None:
    if default_factory is None:
        return None
    return DefaultFactory(
        pyfunc=default_factory["pyfunc"], tsfunc=default_factory["tsfunc"]
    )


def _parse_system_controlled_attrs(
    attrs: dict | None,
) -> SystemControlledAttrs | None:
    if attrs is None:
        return None
    if not isinstance(attrs, dict):
        raise NotImplementedError(attrs)

    if "on_upsert" in attrs:
        attrs = attrs.copy()
        attrs.update(
            {
                "on_create": attrs["on_upsert"],
                "on_create_bypass": attrs.get("on_upsert_bypass"),
                "on_update": attrs["on_upsert"],
                "on_update_bypass": attrs.get("on_upsert_bypass"),
            }
        )

    if "on_create" not in attrs or "on_update" not in attrs:
        raise ValueError(
            "System controlled attributes must have 'on_create', 'on_update', or 'on_upsert' must be defined."
        )

    keys = {}
    for key in ["on_create", "on_update"]:
        if attrs[key] == "ignored":
            keys[key] = "ignored"
        elif attrs[key].find(":") != -1:
            func, args = attrs[key].split(":")
            assert func == "getattr", f"Unsupported function: {func}"
            args = orjson.loads(args)
            keys[key] = GetSCPropValueFunc(
                func=func,
                args=args,
            )
        else:
            raise ValueError(
                f"System controlled attribute '{key}' must be 'ignored' or a function call in the format '<funcname>:<args>'."
            )

        if attrs[key + "_bypass"] is not None:
            if not isinstance(attrs[key + "_bypass"], str):
                raise ValueError(
                    f"System controlled attribute '{key}_bypass' must be a string."
                )
            keys[key + "_bypass"] = attrs[key + "_bypass"]

    return SystemControlledAttrs(
        on_create=keys["on_create"],
        on_create_bypass=keys.get("on_create_bypass"),
        on_update=keys["on_update"],
        on_update_bypass=keys.get("on_update_bypass"),
    )
