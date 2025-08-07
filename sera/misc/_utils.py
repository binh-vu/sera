from __future__ import annotations

import importlib
import inspect
import re
from collections import defaultdict
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Optional,
    Sequence,
    Type,
    TypedDict,
    TypeVar,
    cast,
)

import msgspec
import orjson
import serde.csv
import serde.json
from loguru import logger
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session
from tqdm import tqdm

if TYPE_CHECKING:
    from sera.libs.directed_computing_graph import DirectedComputingGraph

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


def import_attr(attr_ident: str):
    lst = attr_ident.rsplit(".", 1)
    module, cls = lst
    module = importlib.import_module(module)
    return getattr(module, cls)


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


def get_dbclass_deser_func(type: type[T]) -> Callable[[dict], T]:
    """Get a deserializer function for a class in models.db."""
    module, clsname = (
        get_classpath(type)
        .replace(".models.db.", ".models.data.")
        .rsplit(".", maxsplit=1)
    )
    StructType = getattr(importlib.import_module(module), f"Create{clsname}")

    def deser_func(obj: dict):
        record = msgspec.json.decode(orjson.dumps(obj), type=StructType)
        if hasattr(record, "_is_scp_updated"):
            # Skip updating system-controlled properties
            record._is_scp_updated = True

        return record.to_db()

    return deser_func


class LoadTableDataArgs(TypedDict, total=False):
    table: type
    tables: Sequence[type]
    file: Path
    files: Sequence[Path]
    file_deser: Callable[[Path], list[Any]]
    record_deser: Optional[
        Callable[[dict], Any | list[Any]]
        | Callable[[dict, RelTableIndex], Any | list[Any]]
    ]
    table_unique_index: dict[type, list[str]]


class RelTableIndex:
    """An index of relational tables to find a record by its unique property."""

    def __init__(self, cls2index: Optional[dict[str, list[str]]] = None):
        self.table2rows: dict[str, dict[int, Any]] = defaultdict(dict)
        self.table2uniqindex2id: dict[str, dict[str, int]] = defaultdict(dict)
        self.cls2index = cls2index or {}

    def set_index(self, clsname: str, props: list[str]):
        """Set the unique index for a class."""
        self.cls2index[clsname] = props

    def add(self, record: Any):
        clsname = record.__class__.__name__
        self.table2rows[clsname][record.id] = record
        if clsname in self.cls2index:
            for prop in self.cls2index[clsname]:
                self.table2uniqindex2id[clsname][getattr(record, prop)] = record.id

    def get_record(self, clsname: str, uniq_prop: str) -> Optional[Any]:
        tbl = self.table2uniqindex2id[clsname]
        if uniq_prop not in tbl:
            return None
        return self.table2rows[clsname][tbl[uniq_prop]]


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

        reltable_index = RelTableIndex()

        for args in table_data:
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

            if "table_unique_index" in args:
                for tbl in tbls:
                    reltable_index.set_index(
                        tbl.__name__, args["table_unique_index"].get(tbl, [])
                    )

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

            assert "record_deser" in args
            deser = args["record_deser"]
            if deser is None:
                assert len(tbls) == 1
                deser = get_dbclass_deser_func(tbls[0])

            sig = inspect.signature(deser)
            param_count = len(sig.parameters)
            if param_count == 1:
                _deser = cast(Callable[[dict], Any], deser)
                records = [_deser(row) for row in raw_records]
            else:
                assert param_count == 2
                _deser = cast(Callable[[dict, RelTableIndex], Any], deser)
                records = [_deser(row, reltable_index) for row in raw_records]

            for r in tqdm(
                records,
                desc=f"Load {', '.join(tbl.__tablename__ for tbl in tbls)}",
                disable=not verbose,
            ):
                if isinstance(r, Sequence):
                    for x in r:
                        session.merge(x)
                        reltable_index.add(x)
                else:
                    session.merge(r)
                    reltable_index.add(r)

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


def load_data_from_dir(
    engine: Engine,
    create_db_and_tables: Callable[[], None],
    data_dir: Path,
    tables: Sequence[type | tuple[type, Callable[[dict], Any]]],
    verbose: bool = False,
):
    """Load data into the database from a directory"""

    load_args = []

    for tbl in tables:
        if isinstance(tbl, tuple):
            tbl, record_deser = tbl
        else:
            record_deser = None

        file = data_dir / (tbl.__tablename__ + ".json")
        if not file.exists():
            logger.warning(
                "File {} does not exist, skipping loading for {}", file, tbl.__name__
            )
            continue

        load_args.append(
            LoadTableDataArgs(
                table=tbl,
                file=file,
                record_deser=record_deser,
            )
        )

    load_data(engine, create_db_and_tables, load_args, verbose)


async def replay_events(
    engine: AsyncEngine, dcg: DirectedComputingGraph, tables: Sequence[type]
):
    """Replay the events in the DirectedComputingGraph. This is useful to re-run the workflows
    that computes derived data after initial data loading.
    """
    async with AsyncSession(engine, expire_on_commit=False) as session:
        for tbl in tables:
            innode = f"{tbl.__tablename__}.create"
            for record in tqdm(
                session.execute(select(tbl)).scalars(),
                desc=f"Replaying events for {tbl.__tablename__}",
            ):
                await dcg.execute_async(input={innode: record})
