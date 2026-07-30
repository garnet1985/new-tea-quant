"""V2-02 — strategy catalog list."""

# from core.bff.APIs.strategy.blueprint import strategy_api_bp
# from core.bff.APIs.strategy.stack import get_stack
# from core.bff.shared.request import pagination_params
# from core.bff.shared.response import ok


# @strategy_api_bp.route("/v1/strategies/list", methods=["GET"])
# def get_strategies_list():
#     s = get_stack()
#     page, limit = pagination_params()
#     items, total = s.fetch_discovered_strategies_page(page, limit)
#     return ok({"items": items, "total": total, "page": page, "limit": limit})
