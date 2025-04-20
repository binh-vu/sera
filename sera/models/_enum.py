from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from sera.misc import to_snake_case
from sera.models._multi_lingual_string import MultiLingualString


@dataclass
class EnumValue:
    name: str
    value: str | int
    description: MultiLingualString


@dataclass
class Enum:
    """Enum class to represent a set of named values."""

    # name of the enum in the application layer
    name: str
    values: dict[str, EnumValue]

    def __post_init__(self):
        # Ensure that all `value` attributes in EnumValue are unique
        unique_values = {value.value for value in self.values.values()}
        if len(unique_values) != len(self.values):
            value_counts = Counter(value.value for value in self.values.values())
            duplicates = [val for val, count in value_counts.items() if count > 1]
            raise ValueError(
                f"All 'value' attributes in EnumValue must be unique. Duplicates found: {duplicates}"
            )

        # Ensure that all `value` attributes in EnumValue are either all strings or all integers
        if not (self.is_str_enum() or self.is_int_enum()):
            raise ValueError(
                "All 'value' attributes in EnumValue must be either all strings or all integers."
            )

    def get_pymodule_name(self) -> str:
        """Get the python module name of this enum as if there is a python module created to store this enum only."""
        return to_snake_case(self.name)

    def get_tsmodule_name(self) -> str:
        """Get the typescript module name of this enum as if there is a typescript module created to store this enum only."""
        return self.name[0].lower() + self.name[1:]

    def is_str_enum(self) -> bool:
        """Check if this enum is a string enum."""
        return all(isinstance(value.value, str) for value in self.values.values())

    def is_int_enum(self) -> bool:
        """Check if this enum is a int enum."""
        return all(isinstance(value.value, int) for value in self.values.values())
