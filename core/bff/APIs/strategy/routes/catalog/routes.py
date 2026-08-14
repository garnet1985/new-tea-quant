from core.bff.APIs.strategy.api_base import API_BASE_PATH, strategy_api_bp
from core.bff.APIs.strategy.routes.catalog.implementer import impl
from core.bff.shared.response import ok

# ********************************
#     Strategy Catalog
# ********************************

DEFAULT_PAGE = 1
DEFAULT_LIMIT = 10
MAX_LIMIT = 100


@strategy_api_bp.route(
    f"{API_BASE_PATH}/catalog/<int:page>/<int:limit>",
    methods=["GET"],
)
def get_strategies_catalog(page: int, limit: int):
    """GET /api/v1/strategy/catalog/:page/:limit → { items, total, page, limit }."""
    catalog = impl.lazy_load()

    page = max(1, int(page) if page is not None else DEFAULT_PAGE)
    limit = max(1, min(int(limit) if limit is not None else DEFAULT_LIMIT, MAX_LIMIT))

    items, total = catalog.list_strategies(page, limit)

    return ok({"items": items, "total": total, "page": page, "limit": limit})
