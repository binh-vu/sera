from __future__ import annotations

from typing import Optional

import orjson
from sqlalchemy import LargeBinary, TypeDecorator
from sqlalchemy import create_engine as sqlalchemy_create_engine
from sqlalchemy import update


class BaseORM:

    def get_update_query(self):
        q = update(self.__class__)
        args = {}
        for col in self.__table__.columns:  # type: ignore
            val = getattr(self, col.name)
            if col.primary_key:
                q = q.where(getattr(self.__class__, col.name) == val)
            args[col.name] = val

        return q.values(**args)

    def get_update_args(self):
        return {col.name: getattr(self, col.name) for col in self.__table__.columns}  # type: ignore

    @classmethod
    def from_dict(cls, data: dict):
        raise NotImplementedError()


class DataclassType(TypeDecorator):
    """SqlAlchemy Type decorator to serialize dataclasses"""

    impl = LargeBinary
    cache_ok = True

    def __init__(self, cls):
        super().__init__()
        self.cls = cls

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return orjson.dumps(value.to_dict())

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        result = orjson.loads(value)
        return self.cls.from_dict(result)


class ListDataclassType(TypeDecorator):
    """SqlAlchemy Type decorator to serialize list of dataclasses"""

    impl = LargeBinary
    cache_ok = True

    def __init__(self, cls):
        super().__init__()
        self.cls = cls

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return orjson.dumps([x.to_dict() for x in value])

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        result = orjson.loads(value)
        return [self.cls.from_dict(x) for x in result]


class DictDataClassType(TypeDecorator):
    """SqlAlchemy Type decorator to serialize mapping of dataclasses"""

    impl = LargeBinary
    cache_ok = True

    def __init__(self, cls):
        super().__init__()
        self.cls = cls

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return orjson.dumps({k: v.to_dict() for k, v in value.items()})

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        result = orjson.loads(value)
        return {k: self.cls.from_dict(v) for k, v in result.items()}


def create_engine(
    dbconn: str,
    connect_args: Optional[dict] = None,
    debug: bool = False,
):
    if dbconn.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {}
    engine = sqlalchemy_create_engine(dbconn, connect_args=connect_args, echo=debug)
    return engine
