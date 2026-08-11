"""App settings service — userspace database / data.json read-write (no Flask)."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.infra.discovery import Discovery
from core.infra.project_context import ProjectContext
from core.infra.project_context.contracts import (
    DEFAULT_DUCKDB_DOMAINS,
    SUPPORTED_DB_TYPES,
)
from core.bff.shared.file_ops import atomic_write_text

logger = logging.getLogger(__name__)

_DB_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_\-.]+$")


def _database_config_dir() -> Path:
    return ProjectContext.path.get_user_config_root() / "database"


def _write_json(path: Path, data: dict) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(path, text, encoding="utf-8")


def _read_flat_type_config(type_path: Path, database_type: str) -> dict:
    raw = Discovery.file.load_json(type_path) if type_path.exists() else {}
    if not isinstance(raw, dict):
        return {}
    inner = raw.get(database_type)
    if isinstance(inner, dict):
        return dict(inner)
    return dict(raw)


def _duckdb_domains_payload(cfg: Dict[str, Any]) -> Dict[str, str]:
    duck = cfg.get("duckdb") if isinstance(cfg.get("duckdb"), dict) else {}
    domains = duck.get("domains") if isinstance(duck.get("domains"), dict) else {}
    out: Dict[str, str] = {}
    for name, block in domains.items():
        if isinstance(block, dict) and block.get("db_path"):
            out[str(name)] = str(block["db_path"])
    return out


def database_settings_response(cfg: Dict[str, Any]) -> Dict[str, Any]:
    dt = str(cfg.get("database_type") or "duckdb").strip().lower()
    if dt == "duckdb":
        return {
            "database_type": dt,
            "database": "",
            "duckdb_domains": _duckdb_domains_payload(cfg),
        }
    inner = cfg.get(dt) if isinstance(cfg.get(dt), dict) else {}
    name = str(inner.get("database") or "").strip()
    return {"database_type": dt, "database": name, "duckdb_domains": {}}


def get_database_settings() -> Dict[str, Any]:
    cfg = ProjectContext.config.load_database_config()
    return database_settings_response(cfg)


def save_database_settings(payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Return ``(response_body, error_message)``."""
    dt = str(payload.get("database_type") or "").strip().lower()
    if dt not in SUPPORTED_DB_TYPES:
        return None, "database_type 须为 postgresql、mysql 或 duckdb"

    base = _database_config_dir()
    base.mkdir(parents=True, exist_ok=True)

    common_path = base / "common.json"
    common: dict = {}
    if common_path.exists():
        loaded = Discovery.file.load_json(common_path)
        if isinstance(loaded, dict):
            common = dict(loaded)
    common["database_type"] = dt
    _write_json(common_path, common)
    logger.info("[bff.settings] wrote database_type=%s to %s", dt, common_path)

    if dt == "duckdb":
        type_path = base / "duckdb.json"
        if not type_path.is_file():
            _write_json(type_path, {"domains": dict(DEFAULT_DUCKDB_DOMAINS)})
            logger.info("[bff.settings] created default duckdb.json at %s", type_path)
        cfg = ProjectContext.config.load_database_config(dt)
        return database_settings_response(cfg), None

    db_name = str(payload.get("database") or "").strip()
    if not db_name:
        return None, "database（库名）不能为空"
    if len(db_name) > 128 or not _DB_NAME_PATTERN.match(db_name):
        return None, "库名仅允许字母、数字、下划线、连字符与点号，且不超过 128 字符"

    type_path = base / f"{dt}.json"
    inner = _read_flat_type_config(type_path, dt)
    inner["database"] = db_name
    _write_json(type_path, inner)
    logger.info("[bff.settings] wrote database=%r for type=%s to %s", db_name, dt, type_path)
    return {"database_type": dt, "database": db_name, "duckdb_domains": {}}, None


def _get_as_of_latest_completed_trading_date() -> Optional[str]:
    data_config = ProjectContext.config.load_data_config()
    return data_config.get("as_of_latest_completed_trading_date")


def normalize_yyyymmdd(value: Any, field: str, *, required: bool = False) -> Optional[str]:
    if value is None:
        if required:
            raise ValueError(f"{field} 不能为空")
        return None
    raw = str(value).strip().replace("-", "")
    if not raw:
        if required:
            raise ValueError(f"{field} 不能为空")
        return None
    if len(raw) != 8 or not raw.isdigit():
        raise ValueError(f"{field} 须为 YYYYMMDD 格式")
    return raw


def normalize_sample_pool(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        raise ValueError("use_sample_stock_list 须为正整数或留空")
    if n <= 0:
        raise ValueError("use_sample_stock_list 须大于 0")
    return n


def data_settings_response(cfg: Dict[str, Any]) -> Dict[str, Any]:
    sample = cfg.get("use_sample_stock_list")
    sample_out: Optional[int] = None
    if isinstance(sample, int) and sample > 0:
        sample_out = sample
    return {
        "default_start_date": str(cfg.get("default_start_date") or "").strip(),
        "as_of_latest_completed_trading_date": _get_as_of_latest_completed_trading_date(),
        "use_sample_stock_list": sample_out,
        "config_path": str(ProjectContext.path.get_user_config_root() / "data.json"),
    }


def get_data_settings() -> Dict[str, Any]:
    cfg = ProjectContext.config.load_data_config()
    return data_settings_response(cfg)


def save_data_settings(payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    try:
        default_start = normalize_yyyymmdd(
            payload.get("default_start_date"),
            "default_start_date",
            required=True,
        )
        as_of = normalize_yyyymmdd(
            payload.get("as_of_latest_completed_trading_date"),
            "as_of_latest_completed_trading_date",
        )
        sample = normalize_sample_pool(payload.get("use_sample_stock_list"))
    except ValueError as exc:
        return None, str(exc)

    path = ProjectContext.path.get_user_config_root() / "data.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if path.exists():
        loaded = Discovery.file.load_json(path)
        if isinstance(loaded, dict):
            existing = dict(loaded)

    existing["default_start_date"] = default_start
    existing["as_of_latest_completed_trading_date"] = as_of
    existing["use_sample_stock_list"] = sample
    _write_json(path, existing)
    logger.info("[bff.settings] wrote data settings to %s", path)

    cfg = ProjectContext.config.load_data_config()
    return data_settings_response(cfg), None


def run_cache_clear(payload: Dict[str, Any]) -> Dict[str, Any]:
    def _flag(key: str) -> bool:
        return bool(payload.get(key))

    from core.infra.system_actions import SystemActions

    return SystemActions.cache.run(
        clear_db_cache=_flag("clear_db_cache"),
        clear_backtest_results=_flag("clear_backtest_results"),
        clear_scan_results=_flag("clear_scan_results"),
        clear_userspace_ntq=_flag("clear_userspace_ntq"),
    )


def get_trace_settings() -> Dict[str, Any]:
    """Current usage-telemetry consent state (``Trace.consent``)."""
    from core.infra.trace import Trace

    raw = Trace.consent.read()
    return {
        "decided": bool(raw.get("decided")),
        "enabled": bool(raw.get("enabled")),
        "needs_ask": bool(Trace.consent.needs_ask()),
        "decided_at": str(raw.get("decided_at") or ""),
        "source": str(raw.get("source") or ""),
    }


def save_trace_settings(payload: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Persist consent via ``Trace.consent.set``; return ``(body, error)``."""
    if "enabled" not in payload:
        return None, "缺少 enabled 字段"
    enabled = payload.get("enabled")
    if not isinstance(enabled, bool):
        return None, "enabled 须为布尔值"

    from core.infra.trace import Trace

    source = str(payload.get("source") or "settings_ui").strip()[:32] or "settings_ui"
    ok_set = Trace.consent.set(enabled, source=source)
    if not ok_set:
        return None, "保存使用统计偏好失败"
    return get_trace_settings(), None
