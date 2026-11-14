"""Post-process catalog / mutate routes。"""

from __future__ import annotations

import logging

from flask import request

from core.bff.APIs.post_process.api_base import post_process_api_bp
from core.bff.APIs.post_process.implementer import impl as catalog_impl
from core.bff.shared.response import error, ok

logger = logging.getLogger(__name__)


@post_process_api_bp.route("/v1/post-process/adapters", methods=["GET"])
def get_post_process_adapters():
    """GET /v1/post-process/adapters — Adapter 目录。"""
    api = catalog_impl.lazy_load()
    items = api.list_adapters()
    return ok({"items": items, "total": len(items)})


@post_process_api_bp.route("/v1/post-process/processors", methods=["GET"])
def get_post_process_processors():
    """GET /v1/post-process/processors — PostProcessor 方案列表。"""
    api = catalog_impl.lazy_load()
    items = api.list_processors()
    return ok({"items": items, "total": len(items)})


@post_process_api_bp.route(
    "/v1/post-process/processors/<key>/enabled", methods=["POST"]
)
def post_post_process_enabled(key: str):
    """POST …/enabled — body ``{ enabled: bool }``。"""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400)
    if "enabled" not in payload:
        return error("缺少 enabled", 400)
    enabled = bool(payload.get("enabled"))
    api = catalog_impl.lazy_load()
    try:
        item = api.set_enabled(str(key or "").strip(), enabled)
    except ValueError as exc:
        return error(str(exc), 400)
    except Exception:
        logger.exception("set_enabled failed: %s", key)
        return error("写入启用状态失败", 500)
    return ok({"item": item})


@post_process_api_bp.route(
    "/v1/post-process/processors/<key>/adapters", methods=["PUT"]
)
def put_post_process_adapters(key: str):
    """PUT …/adapters — body ``{ adapters: { name: { depends_on: [] } } }``。"""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400)
    adapters = payload.get("adapters")
    if not isinstance(adapters, dict):
        return error("adapters 须为对象", 400)
    api = catalog_impl.lazy_load()
    try:
        item = api.update_adapters(str(key or "").strip(), adapters)
    except ValueError as exc:
        return error(str(exc), 400)
    except Exception:
        logger.exception("update_adapters failed: %s", key)
        return error("写入 adapters 失败", 500)
    return ok({"item": item})
