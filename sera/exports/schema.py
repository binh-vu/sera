from typing import Optional

from sqlalchemy import MetaData, create_engine
from sqlalchemy.schema import CreateTable
from supplier.models.db.supplier import Supplier
from user.models.db.base import Base, engine, get_session
from user.models.db.group import Group
from user.models.db.tenant import Tenant
from user.models.db.user import User

"""
Generate SQL schema from SQLAlchemy models.
"""


def export_prisma_schema() -> str:
    pass


def generate_schema_sql(
    metadata: MetaData, dialect_name: str = "postgresql", echo: bool = False
) -> None:
    """
    Generates and prints the SQL DDL for all tables in the given metadata.

    :param metadata: The SQLAlchemy MetaData object containing table definitions.
    :param dialect_name: The name of the SQL dialect (e.g., 'postgresql', 'mysql', 'sqlite').
    :param echo: If True, the generated SQL will be printed to stdout.
                 This is useful for debugging or capturing the output.
    """
    engine = create_engine(f"{dialect_name}://", echo=echo)
    with engine.connect() as connection:
        for table in metadata.sorted_tables:
            print(CreateTable(table).compile(connection.engine))


def generate_schema_string(metadata: MetaData, dialect_name: str = "postgresql") -> str:
    """
    Generates the SQL DDL for all tables in the given metadata and returns it as a string.

    :param metadata: The SQLAlchemy MetaData object containing table definitions.
    :param dialect_name: The name of the SQL dialect (e.g., 'postgresql', 'mysql', 'sqlite').
    :return: A string containing the SQL DDL.
    """
    engine = create_engine(f"{dialect_name}://")
    sql_statements = []
    # The connection is not strictly necessary for DDL generation for some dialects,
    # but CreateTable().compile() can accept an engine or connection.
    # Using a dummy engine is sufficient here as we only need dialect-specific compilation.
    for table in metadata.sorted_tables:
        sql_statements.append(str(CreateTable(table).compile(engine)).strip() + ";")
    return "\n\n".join(sql_statements)


if __name__ == "__main__":
    with get_session() as session:
        for table in [User, Group, Tenant, Supplier]:
            # for table in Base.metadata.sorted_tables:
            print(CreateTable(table).compile(session.bind), ";")
