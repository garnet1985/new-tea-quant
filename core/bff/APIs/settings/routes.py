"""App settings routes (userspace database config, etc.)."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, Optional

from flask import Blueprint, request

from core.infra.project_context import ProjectContext
from core.infra.discovery import Discovery  # 文件操作
from core.bff.shared.file_ops import atomic_write_text
from core.bff.shared.response import error, ok

logger = logging.getLogger(__name__)

settings_api_bp = Blueprint("settings_api", __name__)

_DB_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_\-.]+$")
_SUPPORTED_DB_TYPES = ("postgresql", "mysql", "duckdb")
_DEFAULT_DUCKDB_DOMAINS = {
    "data": {"db_path": "data.duckdb"},
    "tag": {"db_path": "tag.duckdb"},
    "strategy": {"db_path": "strategy.duckdb"},
}


def _database_config_dir() -> Path:
    return ProjectContext.path.get_user_config_root() / "database"


def _read_flat_type_config(type_path: Path, database_type: str) -> dict:
    # 迁移：使用 Discovery.file.load_json 代替 ProjectContext.load_file_content
    raw = Discovery.file.load_json(type_path) if type_path.exists() else {}
    if not isinstance(raw, dict):
        return {}
    inner = raw.get(database_type)
    if isinstance(inner, dict):
        return dict(inner)
    return dict(raw)


def _write_json(path: Path, data: dict) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(path, text, encoding="utf-8")


def _duckdb_domains_payload(cfg: Dict[str, Any]) -> Dict[str, str]:
    duck = cfg.get("duckdb") if isinstance(cfg.get("duckdb"), dict) else {}
    domains = duck.get("domains") if isinstance(duck.get("domains"), dict) else {}
    out: Dict[str, str] = {}
    for name, block in domains.items():
        if isinstance(block, dict) and block.get("db_path"):
            out[str(name)] = str(block["db_path"])
    return out


def _database_settings_response(cfg: Dict[str, Any]) -> Dict[str, Any]:
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


def _get_as_of_latest_completed_trading_date() -> Optional[str]:
    """获取 data.json 的 as_of_latest_completed_trading_date 配置（迁移后）"""
    # 迁移：直接从 data.json 中读取，不通过 ProjectContext
    data_config = ProjectContext.config.load_data_config()
    return data_config.get("as_of_latest_completed_trading_date")


@settings_api_bp.route("/v1/settings/database", methods=["GET"])
def get_database_settings():
    """读取合并后的当前库类型与库名（与 ``ProjectContext.config.load_database_config`` 一致）。"""
    # 迁移：使用 ProjectContext.config（内部调用）
    cfg = ProjectContext.config.load_database_config()
    return ok(_database_settings_response(cfg))


@settings_api_bp.route("/v1/settings/database", methods=["POST"])
def post_database_settings():
    """写入 ``userspace/config/database/common.json`` 与 ``{type}.json``。"""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400)

    dt = str(payload.get("database_type") or "").strip().lower()
    if dt not in _SUPPORTED_DB_TYPES:
        return error("database_type 须为 postgresql、mysql 或 duckdb", 400)

    base = _database_config_dir()
    base.mkdir(parents=True, exist_ok=True)

    common_path = base / "common.json"
    common: dict = {}
    if common_path.exists():
        # 迁移：使用 Discovery.file.load_json 代替 ProjectContext.load_file_content
        loaded = Discovery.file.load_json(common_path)
        if isinstance(loaded, dict):
            common = dict(loaded)
    common["database_type"] = dt
    _write_json(common_path, common)
    logger.info("[bff.settings] wrote database_type=%s to %s", dt, common_path)

    if dt == "duckdb":
        type_path = base / "duckdb.json"
        if not type_path.is_file():
            _write_json(type_path, {"domains": dict(_DEFAULT_DUCKDB_DOMAINS)})
            logger.info("[bff.settings] created default duckdb.json at %s", type_path)
        # 迁移：使用 ProjectContext.config（内部调用）
        cfg = ProjectContext.config.load_database_config(dt)
        return ok(_database_settings_response(cfg))

    db_name = str(payload.get("database") or "").strip()
    if not db_name:
        return error("database（库名）不能为空", 400)
    if len(db_name) > 128 or not _DB_NAME_PATTERN.match(db_name):
        return error("库名仅允许字母、数字、下划线、连字符与点号，且不超过 128 字符", 400)

    type_path = base / f"{dt}.json"
    inner = _read_flat_type_config(type_path, dt)
    inner["database"] = db_name
    _write_json(type_path, inner)
    logger.info("[bff.settings] wrote database=%r for type=%s to %s", db_name, dt, type_path)

    return ok({"database_type": dt, "database": db_name, "duckdb_domains": {}})


def _normalize_yyyymmdd(value: Any, field: str, *, required: bool = False) -> Optional[str]:
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


def _normalize_sample_pool(value: Any) -> Optional[int]:
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


def _data_settings_response(cfg: Dict[str, Any]) -> Dict[str, Any]:
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


@settings_api_bp.route("/v1/settings/data", methods=["GET"])
def get_data_settings():
    """读取合并后的 data.json 关键字段（default_start_date / as-of / 样本池）。"""
    # 迁移：使用 ProjectContext.config（内部调用）
    cfg = ProjectContext.config.load_data_config()
    return ok(_data_settings_response(cfg))


@settings_api_bp.route("/v1/settings/data", methods=["POST"])
def post_data_settings():
    """写入 ``userspace/config/data.json`` 中的数据范围字段。"""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400)

    try:
        default_start = _normalize_yyyymmdd(
            payload.get("default_start_date"),
            "default_start_date",
            required=True,
        )
        as_of = _normalize_yyyymmdd(
            payload.get("as_of_latest_completed_trading_date"),
            "as_of_latest_completed_trading_date",
        )
        sample = _normalize_sample_pool(payload.get("use_sample_stock_list"))
    except ValueError as exc:
        return error(str(exc), 400)

    path = ProjectContext.path.get_user_config_root() / "data.json"
    path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if path.exists():
        # 迁移：使用 Discovery.file.load_json 代替 ProjectContext.load_file_content
        loaded = Discovery.file.load_json(path)
        if isinstance(loaded, dict):
            existing = dict(loaded)

    existing["default_start_date"] = default_start
    existing["as_of_latest_completed_trading_date"] = as_of
    existing["use_sample_stock_list"] = sample
    _write_json(path, existing)
    logger.info("[bff.settings] wrote data settings to %s", path)

    # 迁移：使用 ProjectContext.config（内部调用）
    cfg = ProjectContext.config.load_data_config()
    return ok(_data_settings_response(cfg))


@settings_api_bp.route("/v1/settings/cache/clear", methods=["POST"])
def post_cache_clear():
    """按勾选项清理 userspace 缓存；全局 pipeline 忙时返回 409。"""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400)

    def _flag(key: str) -> bool:
        return bool(payload.get(key))

    from core.infra.system_actions.cache_cleanup.cache_cleanup import run_cache_cleanup

    out = run_cache_cleanup(
        clear_db_cache=_flag("clear_db_cache"),
        clear_backtest_results=_flag("clear_backtest_results"),
        clear_scan_results=_flag("clear_scan_results"),
        clear_userspace_ntq=_flag("clear_userspace_ntq"),
    )
    if not out.get("ok"):
        err = str(out.get("error") or "清理失败")
        if err == "nothing_selected":
            return error("请至少选择一项缓存", 400)
        if err == "pipeline_busy":
            label = str(out.get("label") or "").strip()
            msg = f"当前有任务进行中，请稍后再试{('：' + label) if label else ''}"
            return error(msg, 409)
        return error(err, 400)
    return ok({"cleared": True, "message": str(out.get("message") or "缓存已经全部清理")})
