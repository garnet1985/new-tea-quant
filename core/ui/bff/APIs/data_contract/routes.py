"""Data contract catalog routes — DC-01."""

from flask import Blueprint

from core.ui.bff.APIs.strategy_workbench.helpers import pagination_params
from core.ui.bff.shared.response import ok

from .contract_stack import get_data_contract_stack

data_contract_api_bp = Blueprint("data_contract_api", __name__)


@data_contract_api_bp.route("/v1/data-contracts/list", methods=["GET"])
def get_data_contracts_list():
    """GET /v1/data-contracts/list — paginated data contract catalog."""
    s = get_data_contract_stack()
    page, limit = pagination_params()
    items, total = s.fetch_data_contract_catalog_page(page, limit)
    return ok({"items": items, "total": total, "page": page, "limit": limit})
