from __future__ import annotations

from sera.models import DataProperty, ObjectProperty


def get_python_property_name(prop: DataProperty | ObjectProperty) -> str:
    """Get property name of a property in Python model"""
    if isinstance(prop, ObjectProperty) and prop.target.db is not None:
        # the property value is a foreign key to another table, we should add _id to
        # the end of the property name
        return prop.name + "_id"
    else:
        return prop.name
