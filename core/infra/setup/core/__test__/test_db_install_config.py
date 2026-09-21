from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.infra.setup.core.db_install_config import write_database_install_config


def test_write_duckdb_config(tmp_path: Path) -> None:
    userspace = tmp_path / "userspace"
    write_database_install_config(userspace, {"dbType": "duckdb"})
    common = json.loads(
        (userspace / "system" / "config" / "database" / "common.json").read_text(
            encoding="utf-8"
        )
    )
    assert common["database_type"] == "duckdb"
    duck = json.loads(
        (userspace / "system" / "config" / "database" / "duckdb.json").read_text(
            encoding="utf-8"
        )
    )
    assert "domains" in duck


def test_write_postgres_requires_fields(tmp_path: Path) -> None:
    userspace = tmp_path / "userspace"
    with pytest.raises(RuntimeError, match="host"):
        write_database_install_config(userspace, {"dbType": "postgresql", "host": ""})


def test_write_postgres_config(tmp_path: Path) -> None:
    userspace = tmp_path / "userspace"
    write_database_install_config(
        userspace,
        {
            "dbType": "postgresql",
            "host": "127.0.0.1",
            "port": "5432",
            "database": "ntq",
            "user": "postgres",
            "password": "secret",
            "defaultPgsqlSchema": "public",
        },
    )
    common = json.loads(
        (userspace / "system" / "config" / "database" / "common.json").read_text(
            encoding="utf-8"
        )
    )
    assert common["database_type"] == "postgresql"
    payload = json.loads(
        (userspace / "system" / "config" / "database" / "postgresql.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["postgresql"]["host"] == "127.0.0.1"
    assert payload["postgresql"]["database"] == "ntq"
    assert payload["postgresql"]["user"] == "postgres"
    assert payload["postgresql"]["password"] == "secret"
