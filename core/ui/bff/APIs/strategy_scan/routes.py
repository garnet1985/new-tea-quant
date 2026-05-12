"""Strategy scan routes — trigger + progress.

Path prefix mounted at ``/api`` (see ``core/ui/bff/app.py``).
"""

from flask import Blueprint, request

import logging

from core.ui.bff.shared.response import error, ok

from .scan_stack import get_strategy_scan_stack

logger = logging.getLogger(__name__)


strategy_scan_api_bp = Blueprint("strategy_scan_api", __name__)


def _parse_bool_query(v: str, default: bool = False) -> bool:
    if v is None:
        return default
    raw = str(v).strip().lower()
    if raw == "":
        return default
    if raw in ("1", "true", "yes", "y", "on"):
        return True
    if raw in ("0", "false", "no", "n", "off"):
        return False
    return default


@strategy_scan_api_bp.route(
    "/v1/strategy/<strategy_name>/scan",
    methods=["GET"],
)
def get_strategy_scan_readiness_route(strategy_name: str):
    """GET /v1/strategy/{strategy_name}/scan?demo=0|1 — 仅返回 ``primary_action``（run|rerun），供按钮文案。"""
    s = get_strategy_scan_stack()
    demo = _parse_bool_query(request.args.get("demo"), default=False)
    payload = s.get_scan_readiness(strategy_name=strategy_name, demo=demo)
    return ok(payload)


@strategy_scan_api_bp.route(
    "/v1/strategy/<strategy_name>/scan",
    methods=["POST"],
)
def post_strategy_scan(strategy_name: str):
    """POST /v1/strategy/{strategy_name}/scan?demo=0|1&force=0|1

    - demo: optional query flag, default false.
    - force: optional query flag; when true,跳过磁盘扫描缓存并全量重算。
    """
    s = get_strategy_scan_stack()
    demo = _parse_bool_query(request.args.get("demo"), default=False)
    force = _parse_bool_query(request.args.get("force"), default=False)
    logger.info("[bff.scan] POST scan strategy=%s demo=%s force=%s", strategy_name, demo, force)
    out = s.trigger_strategy_scan_run(strategy_name=strategy_name, demo=demo, force=force)
    if not out.get("is_triggered"):
        reason = str(out.get("reason") or "启动扫描失败")
        status = 409 if "运行中" in reason or "扫描任务" in reason else 400
        logger.warning(
            "[bff.scan] trigger rejected strategy=%s demo=%s force=%s status=%s reason=%s",
            strategy_name,
            demo,
            force,
            status,
            reason,
        )
        return error(reason, status)
    logger.info(
        "[bff.scan] triggered strategy=%s demo=%s force=%s job_id=%s",
        strategy_name,
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
            "strategy_name": strategy_name,
        }
    )


@strategy_scan_api_bp.route(
    "/v1/strategy/<strategy_name>/scan/progress",
    methods=["GET"],
)
def get_strategy_scan_progress(strategy_name: str):
    """GET /v1/strategy/{strategy_name}/scan/progress?job_id=..."""
    s = get_strategy_scan_stack()
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    payload = s.get_scan_progress(strategy_name=strategy_name, job_id=q_job)
    if payload is None:
        return error("任务不存在或与路径不匹配", 404)
    return ok(payload)
