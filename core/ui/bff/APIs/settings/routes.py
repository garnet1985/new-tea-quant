"""App settings routes (userspace database config, etc.)."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from flask import Blueprint, request

from core.infra.project_context.config_manager import ConfigManager
from core.infra.project_context.path_manager import PathManager
from core.ui.bff.shared.file_ops import atomic_write_text
from core.ui.bff.shared.response import error, ok

logger = logging.getLogger(__name__)

settings_api_bp = Blueprint("settings_api", __name__)

_DB_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_\-.]+$")


def _database_config_dir() -> Path:
    return PathManager.userspace() / "config" / "database"


def _read_flat_type_config(type_path: Path, database_type: str) -> dict:
    raw = ConfigManager.load_json(type_path) if type_path.exists() else {}
    if not isinstance(raw, dict):
        return {}
    inner = raw.get(database_type)
    if isinstance(inner, dict):
        return dict(inner)
    return dict(raw)


def _write_json(path: Path, data: dict) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    atomic_write_text(path, text, encoding="utf-8")


@settings_api_bp.route("/v1/settings/database", methods=["GET"])
def get_database_settings():
    """读取合并后的当前库类型与库名（与 ``ConfigManager.load_database_config`` 一致）。"""
    cfg = ConfigManager.load_database_config()
    dt = str(cfg.get("database_type") or "postgresql").strip().lower()
    inner = cfg.get(dt) if isinstance(cfg.get(dt), dict) else {}
    name = str(inner.get("database") or "").strip()
    return ok({"database_type": dt, "database": name})


@settings_api_bp.route("/v1/settings/database", methods=["POST"])
def post_database_settings():
    """写入 ``userspace/config/database/common.json`` 与 ``{type}.json`` 中的 ``database`` 字段。"""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400)

    dt = str(payload.get("database_type") or "").strip().lower()
    if dt not in ("postgresql", "mysql"):
        return error("database_type 须为 postgresql 或 mysql", 400)

    db_name = str(payload.get("database") or "").strip()
    if not db_name:
        return error("database（库名）不能为空", 400)
    if len(db_name) > 128 or not _DB_NAME_PATTERN.match(db_name):
        return error("库名仅允许字母、数字、下划线、连字符与点号，且不超过 128 字符", 400)

    base = _database_config_dir()
    base.mkdir(parents=True, exist_ok=True)

    common_path = base / "common.json"
    common: dict = {}
    if common_path.exists():
        loaded = ConfigManager.load_json(common_path)
        if isinstance(loaded, dict):
            common = dict(loaded)
    common["database_type"] = dt
    _write_json(common_path, common)
    logger.info("[bff.settings] wrote database_type=%s to %s", dt, common_path)

    type_path = base / f"{dt}.json"
    inner = _read_flat_type_config(type_path, dt)
    inner["database"] = db_name
    _write_json(type_path, inner)
    logger.info("[bff.settings] wrote database=%r for type=%s to %s", db_name, dt, type_path)

    return ok({"database_type": dt, "database": db_name})
