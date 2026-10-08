"""Data contract catalog routes — DC-01 / DC-02."""

from flask import Blueprint

from core.bff.shared.request import pagination_params
from core.bff.shared.response import ok

from .implementer import impl as contract_impl

data_contract_api_bp = Blueprint("data_contract_api", __name__)


@data_contract_api_bp.route("/v1/data-contracts/list", methods=["GET"])
def get_data_contracts_list():
    """GET /v1/data-contracts/list — paginated data contract catalog."""
    api = contract_impl.lazy_load()
    page, limit = pagination_params()
    items, total = api.fetch_catalog_page(page, limit)
    return ok({"items": items, "total": total, "page": page, "limit": limit})


@data_contract_api_bp.route("/v1/data-contracts/reload", methods=["POST"])
def post_data_contracts_reload():
    """POST /v1/data-contracts/reload — rediscover system + userspace contracts."""
    api = contract_impl.lazy_load()
    summary = api.reload_catalog()
    page, limit = pagination_params()
    items, total = api.fetch_catalog_page(page, limit)
    return ok(
        {
            "reloaded": True,
            "total": total if total else int(summary.get("total") or 0),
            "items": items,
            "page": page,
            "limit": limit,
        }
    )
