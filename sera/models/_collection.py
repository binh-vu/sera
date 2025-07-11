from __future__ import annotations

from dataclasses import dataclass

from sera.models._class import Class
from sera.models._property import DataProperty, ObjectProperty


@dataclass
class DataCollection:
    """Represent a data collection, which can be a class or a data product created via some transformation."""

    cls: Class

    @property
    def name(self) -> str:
        """Get the name of the collection."""
        return self.cls.name

    def get_pymodule_name(self) -> str:
        """Get the python module name of this collection as if there is a python module created to store this collection only."""
        return self.cls.get_pymodule_name()

    def get_queryable_fields(self) -> set[str]:
        """Get the fields of this collection that can be used in a queries."""
        field_names = set()
        for prop in self.cls.properties.values():
            if prop.db is None or prop.data.is_private:
                # This property is not stored in the database or it's private, so we skip it
                continue
            if (
                isinstance(prop, DataProperty)
                and prop.db is not None
                and not prop.db.is_indexed
            ):
                # This property is not indexed, so we skip it
                continue
            if isinstance(prop, ObjectProperty) and prop.target.db is None:
                # TODO: Implement this! This property is an embedded object property, we need to figure out
                # which necessary properties are queryable and add them to the field names
                continue
            if isinstance(prop, ObjectProperty) and prop.target.db is not None:
                # This property is an object property stored in the database, "_id" is added to the property name
                propname = prop.name + "_id"
            else:
                # This property is a data property or an object property not stored in the database, so we use its name
                propname = prop.name
            field_names.add(propname)
        return field_names

    def get_service_name(self):
        return f"{self.name}Service"
