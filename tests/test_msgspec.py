from __future__ import annotations

from typing import Annotated

import msgspec


def test_system_controlled_fields():
    """Test that a marker `verified` is not settable by the user. It can only be later after init programmatically."""

    class UpsertUser(msgspec.Struct, kw_only=True):
        id: int
        tenant: int
        name: Annotated[str, msgspec.Meta(min_length=1)]

        _verified: bool = False

        def __post_init__(self) -> None:
            self._verified = False

    user1 = UpsertUser(id=1, tenant=1, name="John Doe")
    assert user1._verified is False
    user2 = UpsertUser(id=1, tenant=1, name="John Doe", _verified=True)
    assert user2._verified is False
    user2._verified = True
    assert user2._verified is True
