from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Annotated, Any, Literal, Optional, Sequence

import msgspec
from litestar import status_codes
from litestar.exceptions import HTTPException

from sera.misc import to_snake_case
from sera.models import Cardinality, Class, DataProperty, ObjectProperty
from sera.typing import FieldName, doc

if TYPE_CHECKING:
    from sera.libs.base_service import QueryResult

"""Providing helpers to implement search functionality in HTTP POST request."""


class QueryOp(str, Enum):
    lt = "lt"
    lte = "lte"
    gt = "gt"
    gte = "gte"
    eq = "eq"
    ne = "ne"
    # select records where values are in the given list
    in_ = "in"
    not_in = "not_in"
    # for full text search
    fuzzy = "fuzzy"


class QueryClause(msgspec.Struct):
    field: FieldName
    op: QueryOp
    value: Annotated[Any, doc("query value")]


class FieldOrderClause(msgspec.Struct):
    field: FieldName
    order: Annotated[Literal["asc", "desc"], doc("order direction, 'asc' or 'desc'")]
    prop: Optional[str] = None


class FieldGroupClause(msgspec.Struct):
    field: FieldName
    prop: Optional[str] = None


# queries conditions written in CNF form.
QueryCondition = Annotated[
    Sequence[QueryClause],
    doc("query operations written in CNF form"),
]


class JoinCondition(msgspec.Struct):
    # name of the property in the primary class
    prop: str
    join_type: Annotated[
        Literal["inner", "left", "full"],
        doc("join type, 'inner', 'left', or 'full'"),
    ] = msgspec.field(default="inner")
    fields: Sequence[FieldName] = msgspec.field(default_factory=list)
    conditions: QueryCondition = msgspec.field(default_factory=list)


class Query(msgspec.Struct):
    # list of fields to return in the results
    fields: Sequence[FieldName] = msgspec.field(default_factory=list)
    # conditions to filter the records
    conditions: QueryCondition = msgspec.field(default_factory=list)
    # sort the records by a field or multiple fields
    sorted_by: Sequence[FieldOrderClause] = msgspec.field(default_factory=list)
    # group the records by a field or multiple fields
    group_by: Sequence[FieldGroupClause] = msgspec.field(default_factory=list)
    # join with another classes
    join_conditions: Sequence[JoinCondition] = msgspec.field(default_factory=list)
    # whether to return unique records
    unique: bool = False
    # maximum number of records to return
    limit: Annotated[int, msgspec.Meta(le=1000, ge=1)] = 10
    # number of records to skip before returning results
    offset: Annotated[int, msgspec.Meta(ge=0)] = 0
    # whether to return the total number of records that match the query
    return_total: bool = False

    def validate_and_normalize(
        self,
        cls: Class,
        allowed_fields: set[str],
        allowed_join_fields: Optional[dict[str, set[str]]] = None,
        debug: bool = False,
    ):
        """Validate query against the schema and normalize the field values.

        Args:
            cls: The class schema
            allowed_fields: The set of allowed search field names
            allowed_join_fields: The dict of allowed search fields in joined tables
            debug: Whether to enable debug mode
        """
        if allowed_join_fields is None:
            allowed_join_fields = {}

        for field_name in self.fields:
            if field_name not in cls.properties:
                if debug:
                    raise HTTPException(
                        status_code=status_codes.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid field name: {field_name}",
                    )
                continue
        for groupfield in self.group_by:
            if groupfield.field not in allowed_fields:
                if debug:
                    raise HTTPException(
                        status_code=status_codes.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid group by field name: {groupfield.field}",
                    )
                continue
        for sortfield in self.sorted_by:
            if sortfield.field not in allowed_fields:
                if debug:
                    raise HTTPException(
                        status_code=status_codes.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid sort by field name: {sortfield.field}",
                    )
                continue
        for clause in self.conditions:
            # TODO: check if the operation is allowed for the field
            if clause.field not in allowed_fields:
                if debug:
                    raise HTTPException(
                        status_code=status_codes.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid condition field name: {clause.field}",
                    )
                continue

            # normalize the value based on the field type.
            prop = cls.properties[clause.field]
            assert isinstance(prop, DataProperty)
            if prop.datatype.pytype.is_enum_type():
                # skip enum types -- we directly use it as string.
                continue
            clause.value = FieldTypeValidator.typemap[prop.datatype.pytype.type](
                clause.field, clause.value
            )

        for join_clause in self.join_conditions:
            if join_clause.prop not in allowed_join_fields:
                if debug:
                    raise HTTPException(
                        status_code=status_codes.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid join property: {join_clause.prop}",
                    )
                continue

            target_prop = cls.properties[join_clause.prop]
            if (
                isinstance(target_prop, DataProperty)
                and target_prop.db is not None
                and target_prop.db.foreign_key is not None
            ):
                # we have this case where ID is also a foreign key
                target_class = target_prop.db.foreign_key
            elif (
                isinstance(target_prop, ObjectProperty)
                and target_prop.target.db is not None
            ):
                target_class = target_prop.target
            else:
                if debug:
                    raise HTTPException(
                        status_code=status_codes.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid join property: {join_clause.prop}",
                    )
                continue

            for field in join_clause.fields:
                if field not in target_class.properties:
                    if debug:
                        raise HTTPException(
                            status_code=status_codes.HTTP_400_BAD_REQUEST,
                            detail=f"Invalid join field: {join_clause.prop}.{field}",
                        )
                    continue
                for condition in join_clause.conditions:
                    if condition.field not in allowed_join_fields[join_clause.prop]:
                        if debug:
                            raise HTTPException(
                                status_code=status_codes.HTTP_400_BAD_REQUEST,
                                detail=f"Invalid join condition field: {join_clause.prop}.{condition.field}",
                            )
                        continue

                    # normalize the value based on the field type.
                    target_prop = target_class.properties[condition.field]
                    assert isinstance(target_prop, DataProperty)
                    if target_prop.datatype.pytype.is_enum_type():
                        # skip enum types -- we directly use it as string.
                        continue
                    condition.value = FieldTypeValidator.typemap[
                        target_prop.datatype.pytype.type
                    ](condition.field, condition.value)

    def prepare_results(
        self, cls: Class, dataschema: dict[str, type], result: QueryResult
    ) -> dict:
        output = {}
        if result.total is not None:
            output["total"] = result.total

        for join_clause in self.join_conditions:
            prop = cls.properties[join_clause.prop]
            if (
                isinstance(prop, DataProperty)
                and prop.db is not None
                and prop.db.foreign_key is not None
            ):
                target_cls = prop.db.foreign_key
                cardinality = Cardinality.ONE_TO_ONE
                # the property storing the SQLAlchemy relationship of the foreign key
                source_relprop = prop.name + "_relobj"
            else:
                assert isinstance(prop, ObjectProperty)
                target_cls = prop.target
                cardinality = prop.cardinality
                source_relprop = prop.name

            target_name = target_cls.name
            assoc_targetrel_name = to_snake_case(target_name)

            deser_func = dataschema[target_name].from_db

            if target_name not in output:
                output[target_name] = []

            if cardinality == Cardinality.MANY_TO_MANY:
                # for many-to-many, we have a middle object (association tables)
                # because it's a list, we don't need to handle outer join because we don't have null values in the list
                output[target_name].extend(
                    deser_func(getattr(item, assoc_targetrel_name))
                    for record in result.records
                    for item in getattr(record, source_relprop)
                )
            elif cardinality == Cardinality.ONE_TO_MANY:
                # A -> B is 1:N, A.id is stored in B, this does not supported in SERA yet so we do not need
                # to implement it
                raise NotImplementedError()
            else:
                if join_clause.join_type != "inner":
                    output[target_name].extend(
                        deser_func((val := getattr(record, source_relprop)))
                        for record in result.records
                        if val is not None
                    )
                else:
                    output[target_name].extend(
                        deser_func(getattr(record, source_relprop))
                        for record in result.records
                    )

        deser_func = dataschema[cls.name].from_db
        output[cls.name] = [deser_func(record) for record in result.records]

        return output


class FieldTypeValidator:

    @staticmethod
    def normalize_str(field: str, val: Any):
        if not isinstance(val, str):
            raise HTTPException(
                status_code=status_codes.HTTP_400_BAD_REQUEST,
                detail=f"Invalid value for field '{field}': Expected string",
            )
        return val

    @staticmethod
    def normalize_int(field: str, val: Any):
        if not isinstance(val, int):
            raise HTTPException(
                status_code=status_codes.HTTP_400_BAD_REQUEST,
                detail=f"Invalid value for field '{field}': Expected int",
            )
        return val

    @staticmethod
    def normalize_float(field: str, val: Any):
        if not isinstance(val, float):
            raise HTTPException(
                status_code=status_codes.HTTP_400_BAD_REQUEST,
                detail=f"Invalid value for field '{field}': Expected float",
            )
        return val

    @staticmethod
    def normalize_bool(field: str, val: Any):
        if not isinstance(val, bool):
            raise HTTPException(
                status_code=status_codes.HTTP_400_BAD_REQUEST,
                detail=f"Invalid value for field '{field}': Expected bool",
            )
        return val

    @staticmethod
    def normalize_date(field: str, val: Any):
        if not isinstance(val, str):
            raise HTTPException(
                status_code=status_codes.HTTP_400_BAD_REQUEST,
                detail=f"Invalid value for field '{field}': Expected date",
            )

        try:
            # Parse ISO format date string to date object
            parsed_date = (
                datetime.fromisoformat(val.replace("Z", "+00:00"))
                .astimezone(timezone.utc)
                .date()
            )
            return parsed_date
        except ValueError:
            raise HTTPException(
                status_code=status_codes.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format for field '{field}': Expected ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)",
            )

    @staticmethod
    def normalize_datetime(field: str, val: Any):
        if not isinstance(val, str):
            raise HTTPException(
                status_code=status_codes.HTTP_400_BAD_REQUEST,
                detail=f"Invalid value for field '{field}': Expected date",
            )

        try:
            # Parse ISO format date string to date object
            parsed_dt = datetime.fromisoformat(val.replace("Z", "+00:00")).astimezone(
                timezone.utc
            )
            return parsed_dt
        except ValueError:
            raise HTTPException(
                status_code=status_codes.HTTP_400_BAD_REQUEST,
                detail=f"Invalid date format for field '{field}': Expected ISO format (YYYY-MM-DDTHH:MM:SS)",
            )

    typemap = {
        "str": normalize_str,
        "int": normalize_int,
        "float": normalize_float,
        "bool": normalize_bool,
        "date": normalize_date,
        "datetime": normalize_datetime,
    }
