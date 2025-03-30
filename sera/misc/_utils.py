from __future__ import annotations

import re
from typing import Any, Callable, Iterable, Optional, TypeVar

T = TypeVar("T")


def to_snake_case(camelcase: str) -> str:
    """Convert camelCase to snake_case."""
    snake = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", camelcase)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", snake)
    return snake.lower()


def to_camel_case(snake: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def to_pascal_case(snake: str) -> str:
    """Convert snake_case to PascalCase."""
    components = snake.split("_")
    return "".join(x.title() for x in components)


def assert_isinstance(x: Any, cls: type[T]) -> T:
    if not isinstance(x, cls):
        raise Exception(f"{type(x)} doesn't match with {type(cls)}")
    return x


def assert_not_null(x: Optional[T]) -> T:
    assert x is not None
    return x


def filter_duplication(
    lst: Iterable[T], key_fn: Optional[Callable[[T], Any]] = None
) -> list[T]:
    keys = set()
    new_lst = []
    if key_fn is not None:
        for item in lst:
            k = key_fn(item)
            if k in keys:
                continue

            keys.add(k)
            new_lst.append(item)
    else:
        for k in lst:
            if k in keys:
                continue
            keys.add(k)
            new_lst.append(k)
    return new_lst
