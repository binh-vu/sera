from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional, Sequence, Type, TypedDict, TypeVar

import serde.csv
import serde.json
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


class LoadTableDataArgs(TypedDict, total=False):
    table: type
    tables: Sequence[type]
    file: Path
    files: Sequence[Path]
    file_deser: Callable[[Path], list[dict]]
    record_deser: Callable[[dict], Any | list[Any]]


def load_data(
    engine: Engine,
    create_db_and_tables: Callable[[], None],
    table_data: Sequence[LoadTableDataArgs],
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

        for args in tqdm(table_data, disable=not verbose, desc="Loading data"):
            if "table" in args:
                tbls = [args["table"]]
            elif "tables" in args:
                tbls = args["tables"]
            else:
                raise ValueError("Either 'table' or 'tables' must be provided in args.")

            if "file" in args:
                assert isinstance(args["file"], Path), "File must be a Path object."
                files = [args["file"]]
            elif "files" in args:
                assert all(
                    isinstance(f, Path) for f in args["files"]
                ), "Files must be Path objects."
                files = args["files"]
            else:
                raise ValueError("Either 'file' or 'files' must be provided in args.")

            raw_records = []
            if "file_deser" not in args:
                for file in files:
                    if file.name.endswith(".csv"):
                        raw_records.extend(serde.csv.deser(file, deser_as_record=True))
                    elif file.name.endswith(".json"):
                        raw_records.extend(serde.json.deser(file))
                    else:
                        raise ValueError(f"Unsupported file format: {file.name}")
            else:
                for file in files:
                    raw_records.extend(args["file_deser"](file))

            deser = args["record_deser"]
            records = [deser(row) for row in raw_records]
            for r in tqdm(
                records,
                desc=f"load {', '.join(tbl.__name__ for tbl in tbls)}",
                disable=not verbose,
            ):
                if isinstance(r, Sequence):
                    for x in r:
                        session.merge(x)
                else:
                    session.merge(r)
            session.flush()

            # Reset the sequence for each table
            for tbl in tbls:
                # Check if the table has an auto-incrementing primary key
                if not hasattr(tbl, "__table__") or not tbl.__table__.primary_key:
                    continue

                pk_columns = tbl.__table__.primary_key.columns
                has_foreign_key = any(len(col.foreign_keys) > 0 for col in pk_columns)
                has_auto_increment = any(
                    col.autoincrement and col.type.python_type in (int,)
                    for col in pk_columns
                )
                if has_foreign_key or not has_auto_increment:
                    continue
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
