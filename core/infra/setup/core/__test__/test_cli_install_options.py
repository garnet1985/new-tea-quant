from __future__ import annotations

import pytest

from core.infra.setup.core.cli_install_options import (
    CliInstallOptions,
    db_inputs_from_options,
    validate_cli_install_options,
)


def test_defaults_need_no_flags() -> None:
    validate_cli_install_options(CliInstallOptions())
    assert db_inputs_from_options(CliInstallOptions()) is None


def test_postgres_requires_connection_flags() -> None:
    with pytest.raises(RuntimeError, match="--db-host"):
        validate_cli_install_options(CliInstallOptions(db="postgresql"))


def test_postgres_complete_options_ok() -> None:
    options = CliInstallOptions(
        db="postgresql",
        db_host="127.0.0.1",
        db_name="ntq",
        db_user="postgres",
        db_password="secret",
    )
    validate_cli_install_options(options)
    inputs = db_inputs_from_options(options)
    assert inputs == {
        "dbType": "postgresql",
        "host": "127.0.0.1",
        "port": "5432",
        "database": "ntq",
        "user": "postgres",
        "password": "secret",
        "defaultPgsqlSchema": "public",
    }


def test_connection_flags_without_db_fail() -> None:
    with pytest.raises(RuntimeError, match="--db postgresql"):
        validate_cli_install_options(CliInstallOptions(db_host="127.0.0.1"))


def test_duckdb_rejects_connection_flags() -> None:
    with pytest.raises(RuntimeError, match="DuckDB"):
        validate_cli_install_options(CliInstallOptions(db="duckdb", db_host="127.0.0.1"))


def test_explicit_userspace_must_be_used() -> None:
    options = CliInstallOptions(userspace="/tmp/custom-userspace", db="duckdb")
    validate_cli_install_options(options)
    from core.infra.setup.core.cli_install_options import userspace_inputs_from_options

    inputs = userspace_inputs_from_options(options, "/default/userspace")
    assert inputs["userspaceTargetPath"] == "/tmp/custom-userspace"
    assert inputs["userspaceConflictPolicy"] == "skip"
