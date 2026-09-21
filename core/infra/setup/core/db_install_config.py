"""Write userspace database config from install inputs (CLI flags or UI wizard)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from core.infra.project_context.contracts import DEFAULT_DUCKDB_DOMAINS

from core.infra.setup.core.cli_install_options import DEFAULT_DB_PORTS

_VALID_DB_TYPES = frozenset({"duckdb", "postgresql", "mysql"})


def _load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _dump_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _port_for(db_type: str, raw: Any) -> int:
    if raw in (None, ""):
        return int(DEFAULT_DB_PORTS[db_type])
    return int(raw)


def write_database_install_config(userspace_root: Path, inputs: Mapping[str, Any]) -> Path:
    """
    Persist wizard/CLI database inputs into ``userspace/system/config/database/``.

    Shape matches the UI setup wizard so CLI and BFF share one writer.
    """
    db_type = str((inputs or {}).get("dbType") or "duckdb").strip().lower() or "duckdb"
    if db_type not in _VALID_DB_TYPES:
        raise RuntimeError(f"不支持的数据库类型: {db_type}")

    db_dir = Path(userspace_root) / "system" / "config" / "database"
    db_dir.mkdir(parents=True, exist_ok=True)

    common_json = db_dir / "common.json"
    common_payload = _load_json(common_json)
    common_payload["database_type"] = db_type
    _dump_json(common_json, common_payload)

    detail_json = db_dir / f"{db_type}.json"
    if db_type == "duckdb":
        if not detail_json.is_file():
            _dump_json(detail_json, {"domains": dict(DEFAULT_DUCKDB_DOMAINS)})
        return db_dir

    try:
        port = _port_for(db_type, (inputs or {}).get("port"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"数据库端口无效: {(inputs or {}).get('port')!r}") from exc

    host = str((inputs or {}).get("host") or "").strip()
    database = str((inputs or {}).get("database") or "").strip()
    user = str((inputs or {}).get("user") or "").strip()
    if not host or not database or not user:
        raise RuntimeError(f"{db_type} 需要 host、database、user")

    block: dict[str, Any] = {
        "host": host,
        "port": port,
        "database": database,
        "user": user,
        "password": (inputs or {}).get("password", ""),
    }
    if db_type == "postgresql":
        block["default_pgsql_schema"] = (
            str((inputs or {}).get("defaultPgsqlSchema") or "public").strip() or "public"
        )
    _dump_json(detail_json, {db_type: block})
    return db_dir
