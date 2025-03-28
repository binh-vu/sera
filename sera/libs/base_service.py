from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Generic, Optional, Sequence, TypeVar

from sera.libs.base_orm import BaseORM
from sera.misc import assert_not_null
from sera.models import Class
from sera.typing import FieldName, T, doc
from sqlalchemy import exists, select
from sqlalchemy.orm import Session


class QueryOp(str, Enum):
    lt = "<"
    lte = "<="
    gt = ">"
    gte = ">="
    eq = "="
    ne = "!="
    # select records where values are in the given list
    in_ = "in"
    not_in = "not in"
    # for full text search
    fuzzy = "fuzzy"


Query = Annotated[
    dict[FieldName, dict[QueryOp, Annotated[Any, doc("query value")]]],
    doc("query operations"),
]
R = TypeVar("R", bound=BaseORM)
ID = TypeVar("ID")  # ID of a class


class BaseService(Generic[ID, R]):

    def __init__(self, cls: Class, orm_cls: type[R]):
        self.cls = cls
        self.orm_cls = orm_cls
        self.id_prop = assert_not_null(cls.get_id_property())

        self._cls_id_prop = getattr(self.orm_cls, self.id_prop.name)

    def get(
        self,
        query: Query,
        limit: int,
        offset: int,
        unique: bool,
        sorted_by: list[str],
        group_by: list[str],
        fields: list[str],
        session: Session,
    ) -> Sequence[R]:
        """Retrieving records matched a query.

        Args:
            query: The query to filter the records
            limit: The maximum number of records to return
            offset: The number of records to skip before returning results
            unique: Whether to return unique results only
            sorted_by: list of field names to sort by, prefix a field with '-' to sort that field in descending order
            group_by: list of field names to group by
            fields: list of field names to include in the results
        """
        return []

    def get_by_id(self, id: ID, session: Session) -> Optional[R]:
        """Retrieving a record by ID."""
        q = select(self.orm_cls).where(self._cls_id_prop == id)
        result = session.execute(q).scalar_one_or_none()
        return result

    def has_id(self, id: ID, session: Session) -> bool:
        """Check whether we have a record with the given ID."""
        q = exists().where(self._cls_id_prop == id)
        result = session.query(q).scalar()
        return bool(result)

    def create(self, record: R, session: Session) -> R:
        """Create a new record."""
        session.add(record)
        session.commit()
        return record

    def update(self, record: R, session: Session) -> R:
        """Update an existing record."""
        session.add(record)
        session.commit()
        return record
