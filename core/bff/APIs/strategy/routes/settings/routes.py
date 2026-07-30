from core.bff.APIs.strategy.api_base import API_BASE_PATH, strategy_api_bp
from core.bff.APIs.strategy.routes.settings.implementer import impl
from core.bff.shared.request import json_payload
from core.bff.shared.response import error, ok

# ***********************************************
#     Strategy Settings (options + apply)
# ***********************************************


@strategy_api_bp.route(
    f"{API_BASE_PATH}/settings/portfolio",
    methods=["GET"],
)
def get_settings_portfolio():
    """GET /api/v1/strategy/settings/portfolio → ``portfolio.allocation.mode`` 选项。"""
    settings = impl.lazy_load()
    return ok({"items": settings.items_portfolio()})


@strategy_api_bp.route(
    f"{API_BASE_PATH}/settings/sampling",
    methods=["GET"],
)
def get_settings_sampling():
    """GET /api/v1/strategy/settings/sampling → ``sampling.strategy`` 选项。"""
    settings = impl.lazy_load()
    return ok({"items": settings.items_sampling()})


@strategy_api_bp.route(
    f"{API_BASE_PATH}/settings/simulation",
    methods=["GET"],
)
def get_settings_simulation():
    """GET /api/v1/strategy/settings/simulation → ``simulation.assumption.template`` 选项。"""
    settings = impl.lazy_load()
    return ok({"items": settings.items_simulation()})


@strategy_api_bp.route(
    f"{API_BASE_PATH}/settings/risk-control",
    methods=["GET"],
)
def get_settings_risk_control():
    """GET /api/v1/strategy/settings/risk-control → ``skip_enter_when`` 标签。"""
    settings = impl.lazy_load()
    return ok({"items": settings.items_risk_control()})


@strategy_api_bp.route(
    f"{API_BASE_PATH}/settings/market-rules",
    methods=["GET"],
)
def get_settings_market_rules():
    """GET /api/v1/strategy/settings/market-rules → 根级 ``market_profile`` 选项。"""
    settings = impl.lazy_load()
    return ok({"items": settings.items_market_rules()})


@strategy_api_bp.route(
    f"{API_BASE_PATH}/settings/apply/<version_id>/<path:strategy_key_or_name>",
    methods=["POST"],
)
def post_settings_apply(version_id: str, strategy_key_or_name: str):
    """
    POST /api/v1/strategy/settings/apply/:version_id/:strategy_key_or_name

    将指定工作台版本的 settings 写回 userspace ``settings.py``。
    Body 可选 ``{ "pretty": bool }``。
    """
    settings = impl.lazy_load()
    payload = json_payload()
    raw_pretty = payload.get("pretty", False) if isinstance(payload, dict) else False
    pretty = raw_pretty if isinstance(raw_pretty, bool) else bool(raw_pretty)

    try:
        out, err = settings.apply_to_userspace(
            strategy_key_or_name=strategy_key_or_name,
            version_id=version_id,
            pretty=pretty,
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)

    if err:
        if err == "version_id 无效":
            return error(err, 400)
        if err == "快照不存在":
            return error(err, 404)
        if err == "存储不可用":
            return error(err, 503)
        if err.startswith("写盘失败") or err.startswith("更新快照时间失败"):
            return error(err, 500)
        return error(err, 400)
    return ok(out)
