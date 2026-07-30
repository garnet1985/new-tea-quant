from core.bff.APIs.strategy.routes.base import API_BASE_PATH, strategy_api_bp
from core.bff.APIs.strategy.stack import get_stack
from core.bff.shared.response import ok

# ********************************
#     Strategy Settings
# ********************************

# TODO: url need to update to /strategy/settings/portfolio
@strategy_api_bp.route(
    f"{API_BASE_PATH}/settings/capital-allocation-strategies",
    methods=["GET"],
)
def get_settings_capital_allocation_strategies():
    s = get_stack()
    return ok({"items": s.items_capital_allocation_strategies()})

# TODO: url need to update to /strategy/settings/sampling
@strategy_api_bp.route(
    f"{API_BASE_PATH}/settings/sampling-strategies",
    methods=["GET"],
)
def get_settings_sampling_strategies():
    s = get_stack()
    return ok({"items": s.items_sampling_strategies()})

# TODO: url need to update to /strategy/settings/simulation
@strategy_api_bp.route(
    f"{API_BASE_PATH}/settings/simulation-templates",
    methods=["GET"],
)
def get_settings_simulation_templates():
    s = get_stack()
    return ok({"items": s.items_simulation_templates()})

# TODO: url need to update to /strategy/settings/risk-control
@strategy_api_bp.route(
    f"{API_BASE_PATH}/settings/skip-investment-when",
    methods=["GET"],
)
def get_settings_skip_investment_when():
    """URL 兼容旧路径；语义为 ``simulation.risk_control.skip_enter_when``。"""
    s = get_stack()
    return ok({"items": s.items_skip_investment_when()})

# TODO: url need to update to /strategy/settings/market-rules
@strategy_api_bp.route(
    f"{API_BASE_PATH}/settings/market-profiles",
    methods=["GET"],
)
def get_settings_market_profiles():
    s = get_stack()
    return ok({"items": s.items_market_profiles()})
