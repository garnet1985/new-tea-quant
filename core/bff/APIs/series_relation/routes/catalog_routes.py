"""Series relation catalog routes."""

from flask import request

from core.bff.APIs.series_relation.api_base import series_relation_api_bp
from core.bff.shared.request import pagination_params
from core.bff.shared.response import error, ok

from .catalog_implementer import catalog_impl


@series_relation_api_bp.route("/v1/series-relations/list", methods=["GET"])
def get_series_relations_list():
    """GET /v1/series-relations/list"""
    api = catalog_impl.lazy_load()
    page, limit = pagination_params()
    items, total = api.fetch_page(page, limit)
    return ok({"items": items, "total": total, "page": page, "limit": limit})


@series_relation_api_bp.route("/v1/series-relations/<path:key>", methods=["GET"])
def get_series_relation_scene(key: str):
    """GET /v1/series-relations/<key>"""
    api = catalog_impl.lazy_load()
    payload = api.get_scene(key)
    if not payload.get("success"):
        return error(str(payload.get("error") or "未找到"), http_status=404)
    return ok(payload)


@series_relation_api_bp.route("/v1/series-relations/<path:key>", methods=["PUT"])
def put_series_relation_scene(key: str):
    """PUT /v1/series-relations/<key> — body: { settings: {...} }"""
    body = request.get_json(silent=True) or {}
    settings = body.get("settings")
    if not isinstance(settings, dict):
        return error("body.settings 必须是 object", http_status=400)
    api = catalog_impl.lazy_load()
    payload = api.save_scene(key, settings)
    if not payload.get("success"):
        return error(
            str(payload.get("error") or "保存失败"),
            http_status=400,
            extra={"errors": payload.get("errors") or []},
        )
    return ok(payload)
