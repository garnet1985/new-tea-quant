"""Data source catalog routes — DS-01."""

from flask import Blueprint, request

from core.bff.shared.request import pagination_params
from core.bff.shared.response import error, ok

from .implementer import impl as source_impl
from .renew_launcher import DataRenewLauncher

data_source_api_bp = Blueprint("data_source_api", __name__)


@data_source_api_bp.route("/v1/data-sources/list", methods=["GET"])
def get_data_sources_list():
    """GET /v1/data-sources/list — paginated data source catalog (static fields only)."""
    api = source_impl.lazy_load()
    page, limit = pagination_params()
    items, total, data_end = api.fetch_catalog_page(page, limit)
    return ok(
        {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "data_end": data_end,
        }
    )


@data_source_api_bp.route("/v1/data-sources/freshness", methods=["GET"])
def get_data_sources_freshness():
    """GET /v1/data-sources/freshness — lazy DB freshness vs data.json as-of."""
    api = source_impl.lazy_load()
    names_param = str(request.args.get("names") or "").strip()
    names = (
        [part.strip() for part in names_param.split(",") if part.strip()]
        if names_param
        else None
    )
    items, data_end = api.fetch_freshness(names)
    return ok({"items": items, "data_end": data_end})


@data_source_api_bp.route("/v1/data-sources/renew", methods=["GET"])
def get_data_sources_renew():
    """GET /v1/data-sources/renew — 当前是否在跑数据更新。"""
    return ok(DataRenewLauncher.status())


@data_source_api_bp.route("/v1/data-sources/renew", methods=["POST"])
def post_data_sources_renew():
    """POST /v1/data-sources/renew — 更新全部，或 body.source 指定一项。"""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400)
    source = payload.get("source")
    if source is not None and not isinstance(source, str):
        return error("source 须为字符串", 400)
    result = DataRenewLauncher.trigger(source)
    if not result.get("is_triggered"):
        return error(str(result.get("reason") or "无法开始更新"), 409)
    return ok(result)
