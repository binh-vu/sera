from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal, Optional

from msgspec import UNSET

from sera.models._constraints import Constraint
from sera.models._datatype import DataType
from sera.models._default import DefaultFactory
from sera.models._multi_lingual_string import MultiLingualString
from sera.typing import UnsetType

if TYPE_CHECKING:
    from sera.models._class import Class


class ForeignKeyOnDelete(str, Enum):
    CASCADE = "cascade"
    SET_NULL = "set null"
    RESTRICT = "restrict"

    def to_sqlalchemy(self) -> str:
        if self == ForeignKeyOnDelete.CASCADE:
            return "CASCADE"
        elif self == ForeignKeyOnDelete.SET_NULL:
            return "SET NULL"
        elif self == ForeignKeyOnDelete.RESTRICT:
            return "RESTRICT"
        raise NotImplementedError(self)


class ForeignKeyOnUpdate(str, Enum):
    CASCADE = "cascade"
    DELETE = "delete"
    RESTRICT = "restrict"

    def to_sqlalchemy(self) -> str:
        if self == ForeignKeyOnUpdate.CASCADE:
            return "CASCADE"
        elif self == ForeignKeyOnUpdate.DELETE:
            return "DELETE"
        elif self == ForeignKeyOnUpdate.RESTRICT:
            return "RESTRICT"
        raise NotImplementedError(self)


class Cardinality(str, Enum):
    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:N"

    def is_star_to_many(self) -> bool:
        return self in [
            Cardinality.ONE_TO_MANY,
            Cardinality.MANY_TO_MANY,
        ]


@dataclass(kw_only=True)
class GetSCPropValueFunc:

    func: Literal["getattr"]
    args: tuple[str, ...]


@dataclass(kw_only=True)
class SystemControlledAttrs:
    """Attributes for a system-controlled property."""

    on_create_bypass: Optional[str]
    on_create: Literal["ignored"] | GetSCPropValueFunc
    on_update_bypass: Optional[str]
    on_update: Literal["ignored"] | GetSCPropValueFunc

    def is_on_create_value_updated(self) -> bool:
        return isinstance(self.on_create, GetSCPropValueFunc)

    def get_on_create_update_func(self) -> GetSCPropValueFunc:
        assert isinstance(self.on_create, GetSCPropValueFunc)
        return self.on_create

    def is_on_create_ignored(self) -> bool:
        return self.on_create == "ignored"

    def is_on_update_ignored(self) -> bool:
        return self.on_update == "ignored"

    def is_on_update_value_updated(self) -> bool:
        return isinstance(self.on_update, GetSCPropValueFunc)

    def get_on_update_update_func(self) -> GetSCPropValueFunc:
        assert isinstance(self.on_update, GetSCPropValueFunc)
        return self.on_update


@dataclass(kw_only=True)
class PropDataAttrs:
    """Storing other attributes for generating data model (upsert & public) -- this is different from a db model"""

    # whether this property is private and cannot be accessed by the end users
    # meaning the public data model will not include this property
    # default it is false
    is_private: bool = False

    # whether this data model has a different data type than the one from the database
    datatype: Optional[DataType] = None

    # list of constraints applied to the data model's field
    constraints: list[Constraint] = field(default_factory=list)

    # if this property is controlled by the system, the attributes for the system-controlled property
    system_controlled: Optional[SystemControlledAttrs] = None

    # default value of this property if it is not provided (then optional is false by default)
    default_value: Any | UnsetType = UNSET


@dataclass(kw_only=True)
class Property:
    """Represent a property of a class."""

    # name of the property in the application layer
    name: str = field(
        metadata={
            "description": "Name of the property in the application layer, so it must be a valid Python identifier"
        }
    )
    # human-readable name of the property
    label: MultiLingualString
    # human-readable description of the property
    description: MultiLingualString
    # other attributes for generating data model such as upsert and return.
    data: PropDataAttrs = field(default_factory=PropDataAttrs)
    # whether this property is optional or not
    is_optional: bool = False


@dataclass(kw_only=True)
class DataPropDBInfo:
    """Represent database information for a data property."""

    # whether this property is a primary key or not
    is_primary_key: bool = False
    # if this property is an integer primary key, whether it is auto-incremented or not
    is_auto_increment: bool = False
    # whether this property contains unique values
    is_unique: bool = False
    # whether this property is indexed or not
    is_indexed: bool = False
    # this is used in conjunction with is_primary_key = True for the case of
    # extending a table with frequently updated properties. The value for the `foreign_key`
    # will be a target class. The cardinality is one-to-one, on target class deletion,
    # this class will be deleted as well (because it's an extended table of the target class).
    # on source (this class) deletion, the target class will not be deleted.
    foreign_key: Optional[Class] = None


@dataclass(kw_only=True)
class DataProperty(Property):
    # data type of the property
    datatype: DataType
    # default value of this property if it is not provided (then optional is false by default)
    default_value: Optional[str | int | bool] = None
    # default value factory of this property if it is not provided
    default_factory: Optional[DefaultFactory] = None

    # other database properties of this property
    db: Optional[DataPropDBInfo] = None

    def get_data_model_datatype(self) -> DataType:
        if self.data.datatype is not None:
            return self.data.datatype
        return self.datatype

    def is_diff_data_model_datatype(self):
        return self.data.datatype is not None


@dataclass(kw_only=True)
class ObjectPropDBInfo:
    """Represent database information for an object property."""

    # if the target class is not stored in the database, whether to store this property as a composite class
    # (see SQLAlchemy composite) or embedded (JSON). Note that it doesn't make sense to embed in composite mode
    # if the cardinality is not 1:1
    is_embedded: Optional[Literal["composite", "json"]] = None

    # if the target class is stored in the database, control the cascade behavior
    on_target_delete: ForeignKeyOnDelete = ForeignKeyOnDelete.RESTRICT
    on_target_update: ForeignKeyOnUpdate = ForeignKeyOnUpdate.RESTRICT

    # this is the case for many-to-many relationships
    on_source_delete: ForeignKeyOnDelete = ForeignKeyOnDelete.RESTRICT
    on_source_update: ForeignKeyOnUpdate = ForeignKeyOnUpdate.RESTRICT


@dataclass(kw_only=True)
class ObjectProperty(Property):
    # the target class of the property
    target: Class
    # the cardinality of the property -- is it one-to-one, many-to-one, etc.
    # if the cardinality is many-to-many, a new joint class is going to be generated automatically
    # to store the relationship -- users can overwrite this generated class by define the one with the same
    # name
    cardinality: Cardinality
    # whether this property is stored as a mapping dic[str, Target] or not
    # only valid for *-to-many relationships
    is_map: bool = False
    db: Optional[ObjectPropDBInfo] = None
