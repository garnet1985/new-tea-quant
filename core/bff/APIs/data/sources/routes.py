"""Data source catalog routes — DS-01."""

from flask import Blueprint, request

from core.bff.shared.request import pagination_params
from core.bff.shared.response import ok

from .implementer import impl as source_impl

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
