from __future__ import annotations

from typing import Generic, NamedTuple, Optional, Sequence, TypeVar

from litestar.exceptions import HTTPException
from sqlalchemy import Result, Select, delete, exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import contains_eager, load_only

from sera.libs.base_orm import BaseORM
from sera.libs.search_helper import Query, QueryOp
from sera.misc import assert_not_null, to_snake_case
from sera.models import Cardinality, Class, DataProperty, ObjectProperty

R = TypeVar("R", bound=BaseORM)
ID = TypeVar("ID")  # ID of a class
SqlResult = TypeVar("SqlResult", bound=Result)


class QueryResult(NamedTuple, Generic[R]):
    records: Sequence[R]
    total: Optional[int]


class BaseAsyncService(Generic[ID, R]):

    instance = None

    def __init__(self, cls: Class, orm_classes: dict[str, type[R]]):
        # schema of the class
        self.cls = cls
        self.orm_cls = orm_classes[cls.name]
        self.id_prop = assert_not_null(cls.get_id_property())

        self._cls_id_prop = getattr(self.orm_cls, self.id_prop.name)
        self.is_id_auto_increment = assert_not_null(self.id_prop.db).is_auto_increment

        self.prop2orm: dict[str, type] = {
            prop.name: orm_classes[prop.target.name]
            for prop in cls.properties.values()
            if isinstance(prop, ObjectProperty) and prop.target.db is not None
        }

        # figure out the join clauses so we can join the tables
        # for example, to join between User, UserGroup, and Group
        # the query can look like this:
        # select(User)
        #     .join(UserGroup, UserGroup.user_id == User.id)
        #     .join(Group, Group.id == UserGroup.group_id)
        #     .options(contains_eager(User.group).contains_eager(UserGroup.group))
        self.join_clauses: dict[str, list[dict]] = {}
        for prop in cls.properties.values():
            if (
                isinstance(prop, DataProperty)
                and prop.db is not None
                and prop.db.foreign_key is not None
            ):
                target_tbl = orm_classes[prop.db.foreign_key.name]
                target_cls = prop.db.foreign_key
                source_fk = prop.name
                # the property storing the SQLAlchemy relationship of the foreign key
                source_relprop = prop.name + "_relobj"
                cardinality = Cardinality.ONE_TO_ONE
            elif isinstance(prop, ObjectProperty) and prop.target.db is not None:
                target_tbl = orm_classes[prop.target.name]
                target_cls = prop.target
                source_fk = prop.name + "_id"
                source_relprop = prop.name
                cardinality = prop.cardinality
            else:
                continue

            if cardinality == Cardinality.MANY_TO_MANY:
                # for many-to-many, we need to import the association tables
                assoc_tbl = orm_classes[f"{cls.name}{target_cls.name}"]
                assoc_tbl_source_fk = to_snake_case(cls.name) + "_id"
                assoc_tbl_target_fk = to_snake_case(target_cls.name) + "_id"
                self.join_clauses[prop.name] = [
                    {
                        "class": assoc_tbl,
                        "condition": getattr(assoc_tbl, assoc_tbl_source_fk)
                        == getattr(self.orm_cls, self.id_prop.name),
                        "contains_eager": getattr(self.orm_cls, source_relprop),
                    },
                    {
                        "class": target_tbl,
                        "condition": getattr(assoc_tbl, assoc_tbl_target_fk)
                        == getattr(
                            target_tbl,
                            assert_not_null(target_cls.get_id_property()).name,
                        ),
                        "contains_eager": getattr(
                            assoc_tbl, to_snake_case(target_cls.name)
                        ),
                    },
                ]
            elif cardinality == Cardinality.ONE_TO_MANY:
                # A -> B is 1:N, A.id is stored in B, this does not supported in SERA yet so we do not need
                # to implement it
                raise NotImplementedError()
            else:
                # A -> B is either 1:1 or N:1, we will store the foreign key is in A
                # .join(B, A.<foreign_key> == B.id)
                self.join_clauses[prop.name] = [
                    {
                        "class": target_tbl,
                        "condition": getattr(
                            target_tbl,
                            assert_not_null(target_cls.get_id_property()).name,
                        )
                        == getattr(self.orm_cls, source_fk),
                        "contains_eager": getattr(self.orm_cls, source_relprop),
                    },
                ]

    @classmethod
    def get_instance(cls):
        """Get the singleton instance of the service."""
        if cls.instance is None:
            # assume that the subclass overrides the __init__ method
            # so that we don't need to pass the class and orm_cls
            cls.instance = cls()  # type: ignore[call-arg]
        return cls.instance

    async def search(
        self,
        query: Query,
        session: AsyncSession,
    ) -> QueryResult[R]:
        """Retrieving records matched a query.

        Args:
            query: The search query
            session: The database session
        """
        q = self._select()

        if len(query.fields) > 0:
            q = q.options(
                load_only(*[getattr(self.orm_cls, field) for field in query.fields])
            )

        if query.unique:
            q = q.distinct()

        if len(query.sorted_by) > 0:
            q = q.order_by(
                *[
                    (
                        (
                            getattr(self.orm_cls, field.field).desc()
                            if field.order == "desc"
                            else getattr(self.orm_cls, field.field)
                        )
                        if field.prop is None
                        else (
                            getattr(self.prop2orm[field.prop], field.field).desc()
                            if field.order == "desc"
                            else getattr(self.prop2orm[field.prop], field.field)
                        )
                    )
                    for field in query.sorted_by
                ]
            )

        if len(query.group_by) > 0:
            q = q.group_by(
                *[
                    (
                        getattr(self.orm_cls, field.field)
                        if field.prop is None
                        else getattr(self.prop2orm[field.prop], field.field)
                    )
                    for field in query.group_by
                ]
            )

        for clause in query.conditions:
            if clause.op == QueryOp.eq:
                q = q.where(getattr(self.orm_cls, clause.field) == clause.value)
            elif clause.op == QueryOp.ne:
                q = q.where(getattr(self.orm_cls, clause.field) != clause.value)
            elif clause.op == QueryOp.lt:
                q = q.where(getattr(self.orm_cls, clause.field) < clause.value)
            elif clause.op == QueryOp.lte:
                q = q.where(getattr(self.orm_cls, clause.field) <= clause.value)
            elif clause.op == QueryOp.gt:
                q = q.where(getattr(self.orm_cls, clause.field) > clause.value)
            elif clause.op == QueryOp.gte:
                q = q.where(getattr(self.orm_cls, clause.field) >= clause.value)
            elif clause.op == QueryOp.in_:
                q = q.where(getattr(self.orm_cls, clause.field).in_(clause.value))
            elif clause.op == QueryOp.not_in:
                q = q.where(~getattr(self.orm_cls, clause.field).in_(clause.value))
            else:
                assert clause.op == QueryOp.fuzzy
                # Assuming fuzzy search is implemented as a full-text search
                q = q.where(
                    func.to_tsvector(getattr(self.orm_cls, clause.field)).match(
                        clause.value
                    )
                )

        for join_condition in query.join_conditions:
            for join_clause in self.join_clauses[join_condition.prop]:
                q = q.join(
                    join_clause["class"],
                    join_clause["condition"],
                    isouter=join_condition.join_type == "left",
                    full=join_condition.join_type == "full",
                ).options(contains_eager(join_clause["contains_eager"]))

                print(">>>", join_clause)

        cq = select(func.count()).select_from(q.subquery())
        rq = q.limit(query.limit).offset(query.offset)
        records = self._process_result(await session.execute(rq)).scalars().all()
        if query.return_total:
            total = (await session.execute(cq)).scalar_one()
        else:
            total = None
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
