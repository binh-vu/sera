from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sera.misc import to_snake_case
from sera.models._multi_lingual_string import MultiLingualString
from sera.models._property import DataProperty, ObjectProperty


@dataclass(kw_only=True)
class Index:
    name: str
    columns: list[str]
    unique: bool = False


@dataclass(kw_only=True)
class ClassDBMapInfo:
    """Represent database information for a class."""

    # name of a corresponding table in the database for this class
    table_name: str
    indices: list[Index] = field(default_factory=list)


@dataclass(kw_only=True)
class Class:
    """Represent a class in the schema."""

    # name of the class in the application layer
    name: str = field(
        metadata={
            "description": "Name of the property in the application layer, so it must be a valid Python identifier"
        }
    )
    # human-readable name of the class
    label: MultiLingualString
    # human-readable description of the class
    description: MultiLingualString
    # properties of the class
    properties: dict[str, DataProperty | ObjectProperty]

    # whether to store this class in a table in the database
    db: Optional[ClassDBMapInfo]
    # whether this class is public and we generate a data model for it.
    is_public: bool = True

    def get_id_property(self) -> Optional[DataProperty]:
        """
        Get the ID property of this class.
        The ID property is the one tagged with is_primary_key
        """
        id_props = []
        for prop in self.properties.values():
            if (
                isinstance(prop, DataProperty)
                and prop.db is not None
                and prop.db.is_primary_key
            ):
                assert (
                    self.db is not None
                ), "This class is not stored in the database and thus, cannot have a primary key"
                id_props.append(prop)
        if len(id_props) > 1:
            raise ValueError(
                f"Class {self.name} has more than one primary key property: {', '.join(p.name for p in id_props)}"
            )
        if len(id_props) == 1:
            return id_props[0]
        # if there is no primary key, we return None
        assert (
            self.db is None
        ), f"The class {self.name} is stored in the database and thus, must have a primary key"
        return None

    def get_pymodule_name(self) -> str:
        """Get the python module name of this class as if there is a python module created to store this class only."""
        return to_snake_case(self.name)

    def get_tsmodule_name(self) -> str:
        """Get the typescript module name of this class as if there is a typescript module created to store this class only."""
        return self.name[0].lower() + self.name[1:]
