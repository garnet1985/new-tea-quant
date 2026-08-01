"""App settings routes (userspace database config, etc.)."""

from __future__ import annotations

from flask import Blueprint, request

from core.bff.shared.response import error, ok

from . import service as settings_service

settings_api_bp = Blueprint("settings_api", __name__)


@settings_api_bp.route("/v1/settings/database", methods=["GET"])
def get_database_settings():
    """读取合并后的当前库类型与库名（与 ``ProjectContext.config.load_database_config`` 一致）。"""
    return ok(settings_service.get_database_settings())


@settings_api_bp.route("/v1/settings/database", methods=["POST"])
def post_database_settings():
    """写入 ``userspace/config/database/common.json`` 与 ``{type}.json``。"""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400)
    body, err = settings_service.save_database_settings(payload)
    if err:
        return error(err, 400)
    return ok(body)


@settings_api_bp.route("/v1/settings/data", methods=["GET"])
def get_data_settings():
    """读取合并后的 data.json 关键字段（default_start_date / as-of / 样本池）。"""
    return ok(settings_service.get_data_settings())


@settings_api_bp.route("/v1/settings/data", methods=["POST"])
def post_data_settings():
    """写入 ``userspace/config/data.json`` 中的数据范围字段。"""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400)
    body, err = settings_service.save_data_settings(payload)
    if err:
        return error(err, 400)
    return ok(body)


@settings_api_bp.route("/v1/settings/cache/clear", methods=["POST"])
def post_cache_clear():
    """按勾选项清理 userspace 缓存；全局 pipeline 忙时返回 409。"""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400)

    out = settings_service.run_cache_clear(payload)
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
