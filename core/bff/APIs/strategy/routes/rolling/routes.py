"""策略滚动对照的 HTTP 入口。"""

from flask import request

from core.bff.APIs.strategy.api_base import API_BASE_PATH, strategy_api_bp
from core.bff.APIs.strategy.routes.rolling.implementer import impl as rolling_impl
from core.bff.shared.request import json_payload
from core.bff.shared.response import error, ok


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/rolling/run/progress",
    methods=["GET"],
)
def get_strategy_rolling_run_progress(strategy_key_or_name: str):
    """查询一次滚动对照任务的进度。"""
    rolling = rolling_impl.lazy_load()
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    try:
        payload = rolling.get_run_progress(
            strategy_key_or_name=strategy_key_or_name, job_id=q_job
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    if payload is None:
        return error("未找到该 job 的滚动进度", 404)
    return ok(payload)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/rolling/status",
    methods=["GET"],
)
def get_strategy_rolling_status(strategy_key_or_name: str):
    """查询滚动测试按钮是否可点。"""
    rolling = rolling_impl.lazy_load()
    try:
        return ok(rolling.status(strategy_key_or_name=strategy_key_or_name))
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/rolling/run",
    methods=["POST"],
)
def post_strategy_rolling_run(strategy_key_or_name: str):
    """启动滚动对照。"""
    rolling = rolling_impl.lazy_load()
    payload = json_payload()
    raw_force = payload.get("force_refresh", payload.get("is_force", False))
    force_refresh = raw_force if isinstance(raw_force, bool) else bool(raw_force)
    try:
        out = rolling.submit_run(
            strategy_key_or_name=strategy_key_or_name,
            force_refresh=force_refresh,
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)

    if out.get("is_triggered"):
        return ok(
            {
                "is_triggered": True,
                "job_id": out["job_id"],
                "run_id": out.get("run_id") or out["job_id"],
                "pipeline_id": out.get("pipeline_id") or out["job_id"],
                "pipeline_name": out.get("pipeline_name"),
                "pipeline_kind": out.get("pipeline_kind") or "rolling",
                "pipeline_description": out.get("pipeline_description"),
            }
        )
    reason = str(out.get("reason") or "启动滚动对照失败")
    status = 409 if "运行中" in reason or "系统任务" in reason else 400
    return error(reason, status)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/rolling/report",
    methods=["GET"],
)
def get_strategy_rolling_report(strategy_key_or_name: str):
    """读取当前主 version 的滚动报告。"""
    rolling = rolling_impl.lazy_load()
    try:
        return ok(rolling.build_report(strategy_key_or_name=strategy_key_or_name))
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
