# """V2-04 — simulation option catalogs (URL under /strategy/settings/*)."""

# from core.bff.APIs.strategy.blueprint import strategy_api_bp
# from core.bff.APIs.strategy.stack import get_stack
# from core.bff.shared.response import ok


# @strategy_api_bp.route(
#     "/v1/strategy/settings/capital-allocation-strategies",
#     methods=["GET"],
# )
# def get_settings_capital_allocation_strategies():
#     s = get_stack()
#     return ok({"items": s.items_capital_allocation_strategies()})


# @strategy_api_bp.route(
#     "/v1/strategy/settings/sampling-strategies",
#     methods=["GET"],
# )
# def get_settings_sampling_strategies():
#     s = get_stack()
#     return ok({"items": s.items_sampling_strategies()})


# @strategy_api_bp.route(
#     "/v1/strategy/settings/simulation-templates",
#     methods=["GET"],
# )
# def get_settings_simulation_templates():
#     s = get_stack()
#     return ok({"items": s.items_simulation_templates()})


# @strategy_api_bp.route(
#     "/v1/strategy/settings/skip-investment-when",
#     methods=["GET"],
# )
# def get_settings_skip_investment_when():
#     """URL 兼容旧路径；语义为 ``simulation.risk_control.skip_enter_when``。"""
#     s = get_stack()
#     return ok({"items": s.items_skip_investment_when()})


# @strategy_api_bp.route(
#     "/v1/strategy/settings/market-profiles",
#     methods=["GET"],
# )
# def get_settings_market_profiles():
#     s = get_stack()
#     return ok({"items": s.items_market_profiles()})
