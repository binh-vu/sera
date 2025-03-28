from __future__ import annotations

from pathlib import Path

from sera.make.make_python_model import make_python_relational_model
from sera.models import Schema


def test_make_relational_model(
    schema: Schema,
    myapp_dir: Path,
):
    make_python_relational_model(
        schema, myapp_dir / "models/db", "myapp.models.db", "myapp.models.data"
    )
