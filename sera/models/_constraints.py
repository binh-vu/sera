from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ConstraintName = Literal[
    "url",
    "phone_number",
    "email",
    "not_empty",
    "username",
    "password",
    "whole_number",
    "positive_number",
]


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
            return "msgspec.Meta(min_length=8, max_length=40)"
        elif self.name == "whole_number":
            return "msgspec.Meta(ge=0)"
        elif self.name == "positive_number":
            return "msgspec.Meta(gt=0)"
        elif self.name == "url":
            return r"msgspec.Meta(pattern=r'^(https?|ftp)://[^\s/$.?#].[^\s]*$')"

        raise NotImplementedError()

    def get_typescript_constraint(self) -> str | dict:
        if len(self.args) == 0:
            return self.name
        return {
            "name": self.name,
            "args": self.args,
        }


predefined_constraints: dict[ConstraintName, Constraint] = {
    "phone_number": Constraint("phone_number", ()),
    "email": Constraint("email", ()),
    "not_empty": Constraint("not_empty", ()),
    "username": Constraint("username", ()),
    "password": Constraint("password", ()),
    "whole_number": Constraint("whole_number", ()),
    "positive_number": Constraint("positive_number", ()),
    "url": Constraint("url", ()),
}
