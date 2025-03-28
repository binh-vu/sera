from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from sera.models import parse_schema


@pytest.fixture
def resource_dir() -> Path:
    """
    Fixture that returns the path to the tests/resources directory.

    Returns:
        Path: The path to the tests/resources directory
    """
    return Path(__file__).parent / "resources"


@pytest.fixture
def myapp_dir(resource_dir: Path) -> Path:
    """
    Fixture that returns the path to the tests/resources/myapp directory.
    """
    return resource_dir / "myapp"


@pytest.fixture
def schema(resource_dir: Path):
    """
    Load the schema from the tests/resources/schema folder.
    """
    schema = parse_schema(list((resource_dir / "schema").rglob("*.yml")))
    return schema
