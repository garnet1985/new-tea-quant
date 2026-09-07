from flask import request

from core.bff.APIs.strategy.api_base import API_BASE_PATH, strategy_api_bp
from core.bff.APIs.strategy.helpers.settings_occupancy import (
    SettingsFileConflict,
    SettingsOccupancy,
)
from core.bff.APIs.strategy.routes.settings.implementer import impl
from core.bff.shared.request import json_payload
from core.bff.shared.response import error, ok

# ***********************************************
#     Strategy Settings (options + apply)
# ***********************************************


def _settings_conflict_response(exc: SettingsFileConflict):
    return error(
        str(exc),
        409,
        code="settings_conflict",
        extra=SettingsOccupancy.conflict_extra(exc.occupancy),
    )


def _expected_rev_and_force(payload: dict) -> tuple:
    expected = SettingsOccupancy.expected_rev_from_request(
        payload,
        if_match_header=request.headers.get("If-Match"),
    )
    raw_force = payload.get("force", False) if isinstance(payload, dict) else False
    force = raw_force if isinstance(raw_force, bool) else bool(raw_force)
    return expected, force


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
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/settings/current",
    methods=["GET"],
)
def get_settings_current(strategy_key_or_name: str):
    """
    GET /api/v1/strategy/:strategy_key_or_name/settings/current

    当前 ``settings.py``：字节 rev + 解析正文 + canonical execute 投影。
    不带 version 报告，供 focus / If-Match 探测。
    """
    settings = impl.lazy_load()
    try:
        occupancy = settings.fetch_current_occupancy(strategy_key_or_name)
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(occupancy)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/settings/persist",
    methods=["POST"],
)
def post_settings_persist(strategy_key_or_name: str):
    """
    POST /api/v1/strategy/:strategy_key_or_name/settings/persist

    将编辑器草稿写回 ``settings.py``。Body：``settings``、可选 ``settings_rev`` / ``force``。
    也接受 ``If-Match``。rev 不一致返回 409。
    """
    settings = impl.lazy_load()
    payload = json_payload()
    body_settings = payload.get("settings")
    if body_settings is None or not isinstance(body_settings, dict):
        return error("settings 必须为对象", 400)
    expected_rev, force = _expected_rev_and_force(payload)
    raw_pretty = payload.get("pretty", True)
    pretty = raw_pretty if isinstance(raw_pretty, bool) else bool(raw_pretty)
    try:
        out, err = settings.persist_editor_settings(
            strategy_key_or_name=strategy_key_or_name,
            settings=body_settings,
            pretty=pretty,
            expected_rev=expected_rev,
            force=force,
        )
    except SettingsFileConflict as exc:
        return _settings_conflict_response(exc)
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    if err:
        status = 400
        if err.startswith("写盘失败"):
            status = 500
        return error(err, status)
    return ok(out or {"settings_rev": ""})


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/settings/apply/<version_id>",
    methods=["POST"],
)
def post_settings_apply(strategy_key_or_name: str, version_id: str):
    """
    POST /api/v1/strategy/:strategy_key_or_name/settings/apply/:version_id

    将指定 version 冻结的 settings 写回 userspace ``settings.py``（恢复配置）。
    Body 可选 ``{ "pretty": bool, "settings_rev": str, "force": bool }``。
    """
    settings = impl.lazy_load()
    payload = json_payload()
    raw_pretty = payload.get("pretty", False) if isinstance(payload, dict) else False
    pretty = raw_pretty if isinstance(raw_pretty, bool) else bool(raw_pretty)
    expected_rev, force = _expected_rev_and_force(payload)

    try:
        out, err = settings.apply_to_userspace(
            strategy_key_or_name=strategy_key_or_name,
            version_id=version_id,
            pretty=pretty,
            expected_rev=expected_rev,
            force=force,
        )
    except SettingsFileConflict as exc:
        return _settings_conflict_response(exc)
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
