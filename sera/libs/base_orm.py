from __future__ import annotations

from typing import Optional

import orjson
from msgspec.json import decode, encode
from sqlalchemy import LargeBinary, TypeDecorator
from sqlalchemy import create_engine as sqlalchemy_create_engine
from sqlalchemy import update
from sqlalchemy.ext.asyncio import create_async_engine as sqlalchemy_create_async_engine

from sera.typing import UNSET


class BaseORM:

    def get_update_query(self):
        q = update(self.__class__)
        args = {}
        for col in self.__table__.columns:  # type: ignore
            val = getattr(self, col.name)
            if val is UNSET:
                continue
            if col.primary_key:
                q = q.where(getattr(self.__class__, col.name) == val)
            args[col.name] = val

        return q.values(**args)

    def get_update_args(self):
        table = self.__table__  # type: ignore
        return {
            col.name: val
            for col in table.columns
            if (val := getattr(self, col.name)) is not UNSET
        }

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
        return encode(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decode(value, type=self.cls)


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
        return encode(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decode(value, type=list[self.cls])


class DictDataclassType(TypeDecorator):
    """SqlAlchemy Type decorator to serialize mapping of dataclasses"""

    impl = LargeBinary
    cache_ok = True

    def __init__(self, cls):
        super().__init__()
        self.cls = cls

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return encode(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return decode(value, type=dict[str, self.cls])


def create_engine(
    dbconn: str,
    connect_args: Optional[dict] = None,
    echo: bool = False,
):
    if dbconn.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {}
    engine = sqlalchemy_create_engine(dbconn, connect_args=connect_args, echo=echo)
    return engine


def create_async_engine(
    dbconn: str,
    connect_args: Optional[dict] = None,
    echo: bool = False,
):
    if dbconn.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    else:
        connect_args = {}

    engine = sqlalchemy_create_async_engine(
        dbconn, connect_args=connect_args, echo=echo
    )
    return engine
