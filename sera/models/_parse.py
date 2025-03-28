from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Sequence

import serde.yaml
from sera.models._class import Class, ClassDBMapInfo
from sera.models._datatype import DataType, predefined_datatypes
from sera.models._multi_lingual_string import MultiLingualString
from sera.models._property import (
    Cardinality,
    DataPropDBInfo,
    DataProperty,
    ForeignKeyOnDelete,
    ForeignKeyOnUpdate,
    ObjectPropDBInfo,
    ObjectProperty,
)
from sera.models._schema import Schema


def parse_schema(files: Sequence[Path | str]) -> Schema:
    schema = Schema(classes={})

    # parse all classes
    raw_defs = {}
    for file in files:
        for k, v in serde.yaml.deser(file).items():
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
        db = ClassDBMapInfo(table_name=cls["db"]["table_name"])
    return Class(
        name=clsname,
        label=_parse_multi_lingual_string(cls["label"]),
        description=_parse_multi_lingual_string(cls["desc"]),
        properties={},
        db=db,
    )


def _parse_property(
    schema: Schema, prop_name: str, prop: dict
) -> DataProperty | ObjectProperty:
    if isinstance(prop, str):
        datatype = prop
        if datatype in schema.classes:
            return ObjectProperty(
                name=prop_name,
                label=_parse_multi_lingual_string(prop_name),
                description=_parse_multi_lingual_string(""),
                target=schema.classes[datatype],
                cardinality=Cardinality.ONE_TO_ONE,
                is_private=False,
            )
        else:
            return DataProperty(
                name=prop_name,
                label=_parse_multi_lingual_string(prop_name),
                description=_parse_multi_lingual_string(""),
                datatype=_parse_datatype(datatype),
                is_private=False,
            )

    db = prop.get("db", {})

    assert isinstance(prop, dict), prop
    if "datatype" in prop:
        return DataProperty(
            name=prop_name,
            label=_parse_multi_lingual_string(prop.get("label", prop_name)),
            description=_parse_multi_lingual_string(prop.get("desc", "")),
            datatype=_parse_datatype(prop["datatype"]),
            is_private=prop.get("is_private", False),
            db=(
                DataPropDBInfo(
                    is_primary_key=db.get("is_primary_key", False),
                    is_auto_increment=db.get("is_auto_increment", False),
                    is_unique=db.get("is_unique", False),
                )
                if "db" in prop
                else None
            ),
        )

    assert "target" in prop, prop
    return ObjectProperty(
        name=prop_name,
        label=_parse_multi_lingual_string(prop.get("label", prop_name)),
        description=_parse_multi_lingual_string(prop.get("desc", "")),
        target=schema.classes[prop["target"]],
        cardinality=Cardinality(prop.get("cardinality", "1:1")),
        is_optional=prop.get("is_optional", False),
        is_private=prop.get("is_private", False),
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


def _parse_datatype(datatype: str) -> DataType:
    if datatype.endswith("[]"):
        datatype = datatype[:-2]
        is_list = True
    else:
        is_list = False

    if datatype not in predefined_datatypes:
        raise NotImplementedError(datatype)

    dt = deepcopy(predefined_datatypes[datatype])
    dt.is_list = is_list
    return dt
