"""Data source catalog routes — DS-01."""

from flask import Blueprint, request

from core.bff.APIs.strategy_workbench.helpers import pagination_params
from core.bff.shared.response import ok

from .source_stack import get_data_source_stack

data_source_api_bp = Blueprint("data_source_api", __name__)


@data_source_api_bp.route("/v1/data-sources/list", methods=["GET"])
def get_data_sources_list():
    """GET /v1/data-sources/list — paginated data source catalog (static fields only)."""
    s = get_data_source_stack()
    page, limit = pagination_params()
    items, total, data_end = s.fetch_data_source_catalog_page(page, limit)
    return ok({"items": items, "total": total, "page": page, "limit": limit, "data_end": data_end})


@data_source_api_bp.route("/v1/data-sources/freshness", methods=["GET"])
def get_data_sources_freshness():
    """GET /v1/data-sources/freshness — lazy DB freshness vs data.json as-of."""
    s = get_data_source_stack()
    names_param = str(request.args.get("names") or "").strip()
    names = [part.strip() for part in names_param.split(",") if part.strip()] if names_param else None
    items, data_end = s.fetch_data_source_freshness(names)
    return ok({"items": items, "data_end": data_end})
