"""决策者 HTTP：会话列表 / 打开 / 现场动作。"""

from __future__ import annotations

from flask import request

from core.bff.APIs.strategy.api_base import API_BASE_PATH, strategy_api_bp
from core.bff.APIs.strategy.routes.decision.implementer import impl as decision_impl
from core.bff.shared.request import json_payload
from core.bff.shared.response import error, ok

# ***********************************************
#     Strategy Decision Maker
#
# Pattern: /v1/strategy/{target}/decision/sessions[/{dm_id}/…]
# 须用字面量 ``decision``，避免被 ``<step>/run`` 吃掉。
# ***********************************************


def _version_id(*candidates: object) -> str | None:
    for raw in candidates:
        text = str(raw or "").strip()
        if text:
            return text
    return None


def _decision_error(exc: BaseException):
    sessions = getattr(exc, "sessions", None)
    if sessions:
        rows = []
        for row in sessions:
            if isinstance(row, dict):
                rows.append(
                    {
                        "dm_id": str(row.get("dm_id") or ""),
                        "status": str(row.get("status") or ""),
                        "current_date": str(row.get("current_date") or ""),
                        "updated_at": str(row.get("updated_at") or ""),
                    }
                )
        return error(
            str(exc),
            409,
            code="ambiguous_sessions",
            extra={"sessions": rows},
        )
    return error(str(exc), 400)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/decision/sessions",
    methods=["GET"],
)
def get_strategy_decision_sessions(strategy_key_or_name: str):
    """
    GET /api/v1/strategy/:strategy_key_or_name/decision/sessions?version=

    D1-01：列出该 version 下各局（默认当前 settings 命中 vid）。
    """
    decision = decision_impl.lazy_load()
    try:
        msg = decision.list_sessions(
            strategy_key_or_name,
            version_id=_version_id(request.args.get("version")),
        )
    except ValueError as exc:
        return _decision_error(exc)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(msg)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/decision/sessions",
    methods=["POST"],
)
def post_strategy_decision_sessions(strategy_key_or_name: str):
    """
    POST /api/v1/strategy/:strategy_key_or_name/decision/sessions

    D1-02：打开或续局。body：``version_id`` / ``session_id`` / ``new_session``。
    多局未完成且未指定 session → 409 ``ambiguous_sessions``。
    """
    decision = decision_impl.lazy_load()
    body = json_payload()
    try:
        msg = decision.open_session(
            strategy_key_or_name,
            version_id=_version_id(body.get("version_id"), request.args.get("version")),
            session_id=str(body.get("session_id") or "").strip() or None,
            new_session=bool(body.get("new_session")),
        )
    except ValueError as exc:
        return _decision_error(exc)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(msg)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/decision/sessions/<dm_id>/pick",
    methods=["POST"],
)
def post_strategy_decision_pick(strategy_key_or_name: str, dm_id: str):
    """
    POST /api/v1/strategy/:strategy_key_or_name/decision/sessions/:dm_id/pick

    D1-05：录入 ``{ local_id, shares }``；也可 ``cash``（金额按手数折股）。同一编号覆盖。
    """
    decision = decision_impl.lazy_load()
    body = json_payload()
    try:
        local_id = int(body.get("local_id"))
    except (TypeError, ValueError):
        return error("local_id 须为整数", 400)
    cash_raw = body.get("cash")
    shares_raw = body.get("shares")
    cash = None
    shares = None
    if cash_raw is not None and str(cash_raw).strip() != "":
        try:
            cash = float(cash_raw)
        except (TypeError, ValueError):
            return error("cash 须为数字", 400)
    elif shares_raw is not None and str(shares_raw).strip() != "":
        try:
            shares = int(shares_raw)
        except (TypeError, ValueError):
            return error("shares 须为整数", 400)
    else:
        return error("请指定 cash 或 shares", 400)
    try:
        msg = decision.set_pick(
            strategy_key_or_name,
            dm_id,
            local_id=local_id,
            shares=shares,
            cash=cash,
            version_id=_version_id(body.get("version_id"), request.args.get("version")),
        )
    except ValueError as exc:
        return _decision_error(exc)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(msg)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/decision/sessions/<dm_id>/done",
    methods=["POST"],
)
def post_strategy_decision_done(strategy_key_or_name: str, dm_id: str):
    """POST …/done — D1-06：看账单，进入 confirming。"""
    decision = decision_impl.lazy_load()
    body = json_payload()
    try:
        msg = decision.done(
            strategy_key_or_name,
            dm_id,
            version_id=_version_id(body.get("version_id"), request.args.get("version")),
        )
    except ValueError as exc:
        return _decision_error(exc)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(msg)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/decision/sessions/<dm_id>/reset",
    methods=["POST"],
)
def post_strategy_decision_reset(strategy_key_or_name: str, dm_id: str):
    """POST …/reset — D1-07：清空当天草稿。"""
    decision = decision_impl.lazy_load()
    body = json_payload()
    try:
        msg = decision.reset(
            strategy_key_or_name,
            dm_id,
            version_id=_version_id(body.get("version_id"), request.args.get("version")),
            keep_draft=bool(body.get("keep_draft")),
        )
    except ValueError as exc:
        return _decision_error(exc)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(msg)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/decision/sessions/<dm_id>/next",
    methods=["POST"],
)
def post_strategy_decision_next(strategy_key_or_name: str, dm_id: str):
    """POST …/next — D1-08：提交当天并推进；``exits`` 为沿途只读出场。"""
    decision = decision_impl.lazy_load()
    body = json_payload()
    try:
        msg = decision.next(
            strategy_key_or_name,
            dm_id,
            version_id=_version_id(body.get("version_id"), request.args.get("version")),
        )
    except ValueError as exc:
        return _decision_error(exc)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(msg)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/decision/sessions/<dm_id>/holdings",
    methods=["GET"],
)
def get_strategy_decision_holdings(strategy_key_or_name: str, dm_id: str):
    """GET …/holdings — D1-09：持仓快照（含这一停的收盘 / 浮动）。"""
    decision = decision_impl.lazy_load()
    try:
        msg = decision.holdings(
            strategy_key_or_name,
            dm_id,
            version_id=_version_id(request.args.get("version")),
        )
    except ValueError as exc:
        return _decision_error(exc)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(msg)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/decision/sessions/<dm_id>/info",
    methods=["GET"],
)
def get_strategy_decision_info(strategy_key_or_name: str, dm_id: str):
    """
    GET …/info?target=&n=&columns=

    D1-10：截至 D 的最近 N 根（默认 60）。``target`` 为当天编号或代码。
    """
    decision = decision_impl.lazy_load()
    target = str(request.args.get("target") or "").strip()
    if not target:
        return error("缺少必填 query 参数 target", 400)
    raw_n = str(request.args.get("n") or "").strip()
    n = None
    if raw_n:
        try:
            n = int(raw_n)
        except ValueError:
            return error("n 须为正整数", 400)
    raw_cols = str(request.args.get("columns") or "").strip()
    columns = [item.strip() for item in raw_cols.split(",") if item.strip()] or None
    try:
        msg = decision.info(
            strategy_key_or_name,
            dm_id,
            target=target,
            n=n,
            columns=columns,
            version_id=_version_id(request.args.get("version")),
        )
    except ValueError as exc:
        return _decision_error(exc)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(msg)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/decision/sessions/<dm_id>/report",
    methods=["GET"],
)
def get_strategy_decision_report(strategy_key_or_name: str, dm_id: str):
    """GET …/report — 终局资金报告（与投资模拟同结构）。"""
    decision = decision_impl.lazy_load()
    try:
        msg = decision.get_report(
            strategy_key_or_name,
            dm_id,
            version_id=_version_id(request.args.get("version")),
        )
    except ValueError as exc:
        return _decision_error(exc)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(msg)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/decision/sessions/<dm_id>",
    methods=["GET"],
)
def get_strategy_decision_session(strategy_key_or_name: str, dm_id: str):
    """GET …/sessions/:dm_id — D1-03：续开该局现场（不推进）。"""
    decision = decision_impl.lazy_load()
    try:
        msg = decision.get_session(
            strategy_key_or_name,
            dm_id,
            version_id=_version_id(request.args.get("version")),
        )
    except ValueError as exc:
        return _decision_error(exc)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(msg)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/decision/sessions/<dm_id>",
    methods=["DELETE"],
)
def delete_strategy_decision_session(strategy_key_or_name: str, dm_id: str):
    """DELETE …/sessions/:dm_id — D1-04：删除一局。"""
    decision = decision_impl.lazy_load()
    try:
        msg = decision.delete_session(
            strategy_key_or_name,
            dm_id,
            version_id=_version_id(request.args.get("version")),
        )
    except ValueError as exc:
        return _decision_error(exc)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    return ok(msg)
