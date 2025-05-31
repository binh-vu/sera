from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
)
from sqlalchemy.schema import CreateTable

# Define your SQLAlchemy engine (dialect matters for SQL output)
# Using a specific dialect helps generate appropriate SQL
# engine = create_engine(
#     "postgresql+psycopg2://user:password@host:port/database", echo=False
# )
# Or for SQLite:
# engine = create_engine("sqlite:///:memory:")
# Or for MySQL:
# engine = create_engine("mysql+mysqlconnector://user:password@host:port/database")


metadata_obj = MetaData()

user_table = Table(
    "users",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("name", String(50)),
    Column("email", String(100), unique=True),
)

address_table = Table(
    "addresses",
    metadata_obj,
    Column("id", Integer, primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("street_name", String(100)),
    Column("city", String(50)),
)

# --- ORM Example ---
# from sqlalchemy.orm import declarative_base, Mapped, mapped_column
# Base = declarative_base()
# metadata_obj = Base.metadata
# class User(Base): # ... (define as above)
# class Address(Base): # ... (define as above)
# -------------------

print("--- Generating DDL for PostgreSQL ---")


def generate_schema_ddl(metadata, engine_dialect):
    for table in metadata.sorted_tables:
        # The CreateTable construct can be compiled to a string
        # specific to the dialect of the engine.
        create_table_ddl = CreateTable(table).compile(dialect=engine_dialect)
        print(str(create_table_ddl).strip() + ";\n")


from sqlalchemy.dialects import postgresql, sqlite

generate_schema_ddl(metadata_obj, postgresql.dialect())

# # Example with a different dialect (e.g., SQLite)
# # Note: You don't need a live connection for this, just the dialect.


# print("\n--- Generating DDL for SQLite ---")
# generate_schema_ddl(metadata_obj, sqlite.dialect())
