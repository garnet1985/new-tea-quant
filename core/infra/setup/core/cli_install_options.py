"""Non-interactive CLI install options (install.py flags)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


DB_TYPES = ("duckdb", "postgresql", "mysql")
CONFLICT_POLICIES = ("skip", "overwrite")
DEFAULT_DB_PORTS = {"postgresql": 5432, "mysql": 3306}


@dataclass
class CliInstallOptions:
    userspace: Optional[str] = None
    userspace_conflict: Optional[str] = None
    db: Optional[str] = None
    db_host: Optional[str] = None
    db_port: Optional[str] = None
    db_name: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_schema: Optional[str] = None

    @property
    def conflict_policy(self) -> str:
        raw = str(self.userspace_conflict or "skip").strip().lower() or "skip"
        return raw if raw in CONFLICT_POLICIES else "skip"

    @property
    def has_db_connection_flags(self) -> bool:
        return any(
            str(value or "").strip()
            for value in (
                self.db_host,
                self.db_port,
                self.db_name,
                self.db_user,
                self.db_password,
                self.db_schema,
            )
        )


def validate_cli_install_options(options: CliInstallOptions) -> None:
    """Fail fast when flags are present but incomplete or contradictory."""
    if options.userspace_conflict is not None:
        policy = str(options.userspace_conflict).strip().lower()
        if policy not in CONFLICT_POLICIES:
            raise RuntimeError(
                f"--userspace-conflict 必须是 skip 或 overwrite，收到: {options.userspace_conflict!r}"
            )

    db = None if options.db is None else str(options.db).strip().lower()
    if db == "":
        db = None
    if db is not None and db not in DB_TYPES:
        raise RuntimeError(f"--db 必须是 duckdb / postgresql / mysql，收到: {options.db!r}")

    if db is None:
        if options.has_db_connection_flags:
            raise RuntimeError(
                "已指定 --db-host / --db-name 等连接参数，请同时指定 --db postgresql 或 --db mysql"
            )
        return

    if db == "duckdb" and options.has_db_connection_flags:
        raise RuntimeError("DuckDB 不使用 --db-host / --db-name 等连接参数")

    if db in ("postgresql", "mysql"):
        missing: list[str] = []
        if not str(options.db_host or "").strip():
            missing.append("--db-host")
        if not str(options.db_name or "").strip():
            missing.append("--db-name")
        if not str(options.db_user or "").strip():
            missing.append("--db-user")
        if missing:
            raise RuntimeError(f"{db} 必须提供: {', '.join(missing)}")
        raw_port = options.db_port
        if raw_port not in (None, ""):
            try:
                int(str(raw_port).strip())
            except (TypeError, ValueError) as exc:
                raise RuntimeError(f"--db-port 无效: {raw_port!r}") from exc


def db_inputs_from_options(options: CliInstallOptions) -> Optional[Dict[str, Any]]:
    """UI-shaped db_connection inputs, or None when the caller did not choose a DB."""
    if options.db is None:
        return None
    db = str(options.db).strip().lower()
    inputs: Dict[str, Any] = {"dbType": db}
    if db == "duckdb":
        return inputs
    port = str(options.db_port or "").strip() or str(DEFAULT_DB_PORTS[db])
    inputs.update(
        {
            "host": str(options.db_host or "").strip(),
            "port": port,
            "database": str(options.db_name or "").strip(),
            "user": str(options.db_user or "").strip(),
            "password": str(options.db_password or ""),
        }
    )
    if db == "postgresql":
        inputs["defaultPgsqlSchema"] = str(options.db_schema or "public").strip() or "public"
    return inputs


def userspace_inputs_from_options(options: CliInstallOptions, default_path: str) -> Dict[str, Any]:
    target = str(options.userspace or "").strip() or default_path
    return {
        "userspaceTargetPath": target,
        "userspaceConflictPolicy": options.conflict_policy,
    }
