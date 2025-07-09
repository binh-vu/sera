from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Type, TypeVar

import serde.csv
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session
from tqdm import tqdm

T = TypeVar("T")

TYPE_ALIASES = {"typing.List": "list", "typing.Dict": "dict", "typing.Set": "set"}

reserved_keywords = {
    "and",
    "or",
    "not",
    "is",
    "in",
    "if",
    "else",
    "elif",
    "for",
    "while",
    "def",
    "class",
    "return",
    "yield",
    "import",
    "from",
    "as",
    "with",
    "try",
    "except",
    "finally",
    "raise",
    "assert",
    "break",
    "continue",
    "pass",
    "del",
    "global",
    "nonlocal",
    "lambda",
    "async",
    "await",
    "True",
    "False",
    "None",
    "self",
}


def to_snake_case(camelcase: str) -> str:
    """Convert camelCase to snake_case."""
    snake = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", camelcase)
    snake = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", snake)
    return snake.lower()


def to_camel_case(snake: str) -> str:
    """Convert snake_case to camelCase."""
    components = snake.split("_")
    out = components[0] + "".join(x.title() for x in components[1:])
    # handle a corner case where the _ is added to the end of the string to avoid reserved keywords
    if snake.endswith("_") and snake[:-1] in reserved_keywords:
        out += "_"
    return out


def to_pascal_case(snake: str) -> str:
    """Convert snake_case to PascalCase."""
    components = snake.split("_")
    out = "".join(x.title() for x in components)
    # handle a corner case where the _ is added to the end of the string to avoid reserved keywords
    if snake.endswith("_") and snake[:-1] in reserved_keywords:
        out += "_"
    return out


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


def load_data(
    engine: Engine,
    create_db_and_tables: Callable[[], None],
    table_files: list[tuple[type, Path]],
    table_desers: dict[type, Callable[[dict], Any]],
    verbose: bool = False,
):
    """
    Load data into the database from specified CSV files.

    Args:
        engine: SQLAlchemy engine to connect to the database.
        create_db_and_tables: Function to create database and tables.
        table_files: List of tuples containing the class type and the corresponding CSV file path.
        table_desers: Dictionary mapping class types to their deserializer functions.
        verbose: If True, show progress bars during loading.
    """
    with Session(engine) as session:
        create_db_and_tables()

        for tbl, file in tqdm(table_files, disable=not verbose, desc="Loading data"):
            if file.name.endswith(".csv"):
                records = serde.csv.deser(file, deser_as_record=True)
            else:
                raise ValueError(f"Unsupported file format: {file.name}")
            deser = table_desers[tbl]
            records = [deser(row) for row in records]
            for r in tqdm(records, desc=f"load {tbl.__name__}", disable=not verbose):
                session.merge(r)
            session.flush()

            # Reset the sequence for each table
            session.execute(
                text(
                    f"SELECT setval('{tbl.__tablename__}_id_seq', (SELECT MAX(id) FROM \"{tbl.__tablename__}\"));"
                )
            )
        session.commit()


def identity(x: T) -> T:
    """Identity function that returns the input unchanged."""
    return x


def get_classpath(type: Type | Callable) -> str:
    if type.__module__ == "builtins":
        return type.__qualname__

    if hasattr(type, "__qualname__"):
        return type.__module__ + "." + type.__qualname__

    # typically a class from the typing module
    if hasattr(type, "_name") and type._name is not None:
        path = type.__module__ + "." + type._name
        if path in TYPE_ALIASES:
            path = TYPE_ALIASES[path]
    elif hasattr(type, "__origin__") and hasattr(type.__origin__, "_name"):
        # found one case which is typing.Union
        path = type.__module__ + "." + type.__origin__._name
    else:
        raise NotImplementedError(type)

    return path
