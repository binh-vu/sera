from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ConstraintName = Literal["phone_number", "email", "not_empty", "username", "password"]


@dataclass
class Constraint:
    name: ConstraintName
    args: tuple

    def get_msgspec_constraint(self) -> str:
        if self.name == "phone_number":
            # the UI will ensure to submit it in E.164 format
            return r"msgspec.Meta(pattern=r'^\+[1-9]\d{1,14}$')"
        elif self.name == "email":
            return r"msgspec.Meta(min_length=3, max_length=254, pattern=r'^[^@]+@[^@]+\.[^@]+$')"
        elif self.name == "not_empty":
            return "msgspec.Meta(min_length=1)"
        elif self.name == "username":
            return (
                "msgspec.Meta(min_length=3, max_length=32, pattern=r'^[a-zA-Z0-9_]+$')"
            )
        elif self.name == "password":
            return "msgspec.Meta(min_length=8, max_length=32)"

        raise NotImplementedError()


predefined_constraints: dict[ConstraintName, Constraint] = {
    "phone_number": Constraint("phone_number", ()),
    "email": Constraint("email", ()),
    "not_empty": Constraint("not_empty", ()),
    "username": Constraint("username", ()),
    "password": Constraint("password", ()),
}
