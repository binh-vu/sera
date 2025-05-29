from __future__ import annotations

from enum import Enum
from math import dist
from typing import Annotated, Any, Generic, NamedTuple, Optional, Sequence, TypeVar

from litestar.exceptions import HTTPException
from sqlalchemy import Result, Select, delete, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from sera.libs.base_orm import BaseORM
from sera.misc import assert_not_null
from sera.models import Class
from sera.typing import FieldName, T, doc


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
SqlResult = TypeVar("SqlResult", bound=Result)


class QueryResult(NamedTuple, Generic[R]):
    records: Sequence[R]
    total: int


class BaseAsyncService(Generic[ID, R]):

    instance = None

    def __init__(self, cls: Class, orm_cls: type[R]):
        self.cls = cls
        self.orm_cls = orm_cls
        self.id_prop = assert_not_null(cls.get_id_property())

        self._cls_id_prop = getattr(self.orm_cls, self.id_prop.name)
        self.is_id_auto_increment = assert_not_null(self.id_prop.db).is_auto_increment

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the service."""
        if cls.instance is None:
            # assume that the subclass overrides the __init__ method
            # so that we don't need to pass the class and orm_cls
            cls.instance = cls()  # type: ignore[call-arg]
        return cls.instance

    async def get(
        self,
        query: Query,
        limit: int,
        offset: int,
        unique: bool,
        sorted_by: list[str],
        group_by: list[str],
        fields: list[str],
        session: AsyncSession,
    ) -> QueryResult[R]:
        """Retrieving records matched a query.

        Args:
            query: The query to filter the records
            limit: The maximum number of records to return
            offset: The number of records to skip before returning results
            unique: Whether to return unique results only
            sorted_by: list of field names to sort by, prefix a field with '-' to sort that field in descending order
            group_by: list of field names to group by
            fields: list of field names to include in the results -- empty means all fields
        """
        q = self._select()
        if fields:
            q = q.options(
                load_only(*[getattr(self.orm_cls, field) for field in fields])
            )
        if unique:
            q = q.distinct()
        if sorted_by:
            for field in sorted_by:
                if field.startswith("-"):
                    q = q.order_by(getattr(self.orm_cls, field[1:]).desc())
                else:
                    q = q.order_by(getattr(self.orm_cls, field))
        if group_by:
            for field in group_by:
                q = q.group_by(getattr(self.orm_cls, field))

        cq = select(func.count()).select_from(q.subquery())
        rq = q.limit(limit).offset(offset)
        records = self._process_result(await session.execute(rq)).scalars().all()
        total = (await session.execute(cq)).scalar_one()
        return QueryResult(records, total)

    async def get_by_id(self, id: ID, session: AsyncSession) -> Optional[R]:
        """Retrieving a record by ID."""
        q = self._select().where(self._cls_id_prop == id)
        result = self._process_result(await session.execute(q)).scalar_one_or_none()
        return result

    async def has_id(self, id: ID, session: AsyncSession) -> bool:
        """Check whether we have a record with the given ID."""
        q = exists().where(self._cls_id_prop == id).select()
        result = (await session.execute(q)).scalar()
        return bool(result)

    async def create(self, record: R, session: AsyncSession) -> R:
        """Create a new record."""
        if self.is_id_auto_increment:
            setattr(record, self.id_prop.name, None)

        try:
            session.add(record)
            await session.flush()
        except IntegrityError:
            raise HTTPException(detail="Invalid request", status_code=409)
        return record

    async def update(self, record: R, session: AsyncSession) -> R:
        """Update an existing record."""
        await session.execute(record.get_update_query())
        return record

    def _select(self) -> Select:
        """Get the select statement for the class."""
        return select(self.orm_cls)

    def _process_result(self, result: SqlResult) -> SqlResult:
        """Process the result of a query."""
        return result

    async def truncate(self, session: AsyncSession) -> None:
        """Truncate the table."""
        await session.execute(delete(self.orm_cls))
