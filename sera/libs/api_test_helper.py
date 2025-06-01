from __future__ import annotations

from litestar import Litestar
from litestar.testing import TestClient


def test_has(
    client: TestClient[Litestar],
    base_url: str,
    exist_records: list[int | str],
    non_exist_records: list[int | str],
) -> None:
    for record in exist_records:
        resp = client.head(f"{base_url}/{record}")
        assert (
            resp.status_code == 204
        ), f"Record {record} should exist but got {resp.status_code}"

    for record in non_exist_records:
        resp = client.head(f"{base_url}/{record}")
        assert (
            resp.status_code == 404
        ), f"Record {record} should not exist but got {resp.status_code}"


def test_get_by_id(
    client: TestClient[Litestar],
    base_url: str,
    exist_records: dict[int | str, dict],
    non_exist_records: list[int | str],
) -> None:
    for record, data in exist_records.items():
        resp = client.get(f"{base_url}/{record}")
        assert (
            resp.status_code == 200
        ), f"Record {record} should exist but got {resp.status_code}"
        assert resp.json() == data

    for record in non_exist_records:
        resp = client.get(f"{base_url}/{record}")
        assert (
            resp.status_code == 404
        ), f"Record {record} should not exist but got {resp.status_code}"
