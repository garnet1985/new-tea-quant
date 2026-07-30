import logging

from flask import request

from core.bff.APIs.strategy.api_base import API_BASE_PATH, strategy_api_bp
from core.bff.APIs.strategy.helpers.query import parse_bool_query
from core.bff.APIs.strategy.routes.runner.implementer import impl as runner_impl
from core.bff.shared.request import json_payload
from core.bff.shared.response import error, ok

# ***********************************************
#     Strategy Runner (workbench run + scan)
#
# Pattern: /v1/strategy/{target}/…/run|progress|scan
# Global: GET …/scan/context
# ***********************************************

logger = logging.getLogger(__name__)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/run/progress",
    methods=["GET"],
)
def get_strategy_run_progress(strategy_key_or_name: str):
    """
    GET /api/v1/strategy/:strategy_key_or_name/run/progress?job_id=

    V2-06b：整次 run 编排进度。须注册在 ``…/<step>/progress`` 之前。
    """
    runner = runner_impl.lazy_load()
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    try:
        payload = runner.get_run_progress(
            strategy_key_or_name=strategy_key_or_name, job_id=q_job
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    if payload is None:
        return error("未找到该 job 的编排进度", 404)
    return ok(payload)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/<step>/run",
    methods=["POST"],
)
def post_strategy_step_run(strategy_key_or_name: str, step: str):
    """
    POST /api/v1/strategy/:strategy_key_or_name/:step/run

    V2-05：启动一步对应的 job；成功时携带 ``job_id`` 轮询 progress。
    """
    runner = runner_impl.lazy_load()
    payload = json_payload()
    settings = payload.get("settings")
    if settings is None or not isinstance(settings, dict):
        return error("settings 必须为对象", 400)

    body_name = payload.get("strategy_name")
    if body_name is not None and str(body_name).strip() not in (
        str(strategy_key_or_name).strip(),
        "",
    ):
        # Allow body strategy_name only when it equals path needle (key or path).
        try:
            path_id = runner.resolve_strategy_name(strategy_key_or_name)
            body_id = runner.resolve_strategy_name(str(body_name).strip())
        except (ValueError, FileNotFoundError) as exc:
            return error(str(exc), 400 if isinstance(exc, ValueError) else 404)
        if body_id != path_id:
            return error("strategy_name 与路径不一致", 400)

    raw_force = payload.get("force_refresh", payload.get("is_force", False))
    force_refresh = raw_force if isinstance(raw_force, bool) else bool(raw_force)

    try:
        out = runner.submit_run(
            strategy_key_or_name=strategy_key_or_name,
            step=step,
            api_settings=settings,
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
                "steps": out.get("steps") or [],
            }
        )
    return ok({"is_triggered": False, "reason": out.get("reason", "未知错误")})


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/<step>/progress",
    methods=["GET"],
)
def get_strategy_step_progress(strategy_key_or_name: str, step: str):
    """
    GET /api/v1/strategy/:strategy_key_or_name/:step/progress?job_id=

    V2-06：legacy 单步进度；新 UI 优先 V2-06b。
    """
    runner = runner_impl.lazy_load()
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    try:
        payload = runner.get_step_progress(
            strategy_key_or_name=strategy_key_or_name,
            step=step,
            job_id=q_job,
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    if payload is None:
        return error("任务不存在或与路径不匹配", 404)
    return ok(payload)


@strategy_api_bp.route(f"{API_BASE_PATH}/scan/context", methods=["GET"])
def get_strategy_scan_context_route():
    """GET /api/v1/strategy/scan/context — 扫描页全局上下文（无 target）。"""
    runner = runner_impl.lazy_load()
    return ok(runner.scan_page_context())


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/scan",
    methods=["GET"],
)
def get_strategy_scan_readiness_route(strategy_key_or_name: str):
    """GET /api/v1/strategy/:strategy_key_or_name/scan?demo=0|1"""
    runner = runner_impl.lazy_load()
    demo = parse_bool_query(request.args.get("demo"), default=False)
    try:
        return ok(
            runner.scan_readiness(
                strategy_key_or_name=strategy_key_or_name, demo=demo
            )
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/scan",
    methods=["POST"],
)
def post_strategy_scan(strategy_key_or_name: str):
    """POST /api/v1/strategy/:strategy_key_or_name/scan?demo=0|1&force=0|1"""
    runner = runner_impl.lazy_load()
    demo = parse_bool_query(request.args.get("demo"), default=False)
    force = parse_bool_query(request.args.get("force"), default=False)
    logger.info(
        "[bff.scan] POST scan strategy=%s demo=%s force=%s",
        strategy_key_or_name,
        demo,
        force,
    )
    try:
        out = runner.trigger_scan(
            strategy_key_or_name=strategy_key_or_name, demo=demo, force=force
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)

    if not out.get("is_triggered"):
        reason = str(out.get("reason") or "启动扫描失败")
        status = 409 if "运行中" in reason or "扫描任务" in reason else 400
        logger.warning(
            "[bff.scan] trigger rejected strategy=%s demo=%s force=%s status=%s reason=%s",
            strategy_key_or_name,
            demo,
            force,
            status,
            reason,
        )
        return error(reason, status)
    logger.info(
        "[bff.scan] triggered strategy=%s demo=%s force=%s job_id=%s",
        strategy_key_or_name,
        demo,
        force,
        out.get("job_id"),
    )
    return ok(
        {
            "is_triggered": True,
            "job_id": out["job_id"],
            "demo": demo,
            "force": force,
            "strategy_name": out.get("strategy_name") or strategy_key_or_name,
        }
    )


@strategy_api_bp.route(
    f"{API_BASE_PATH}/<path:strategy_key_or_name>/scan/progress",
    methods=["GET"],
)
def get_strategy_scan_progress(strategy_key_or_name: str):
    """GET /api/v1/strategy/:strategy_key_or_name/scan/progress?job_id="""
    runner = runner_impl.lazy_load()
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    try:
        payload = runner.scan_progress(
            strategy_key_or_name=strategy_key_or_name, job_id=q_job
        )
    except ValueError as exc:
        return error(str(exc), 400)
    except FileNotFoundError as exc:
        return error(str(exc), 404)
    if payload is None:
        return error("任务不存在或与路径不匹配", 404)
    return ok(payload)
