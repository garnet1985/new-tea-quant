"""Strategy scan routes — trigger + progress.

Path prefix mounted at ``/api`` (see ``core/ui/bff/app.py``).
"""

from flask import Blueprint, request

from core.modules.strategy.services.launcher.scanner_run import (
    get_scan_progress,
    trigger_strategy_scan_run,
)
from core.ui.bff.shared.response import error, ok


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
    methods=["POST"],
)
def post_strategy_scan(strategy_name: str):
    """POST /v1/strategy/{strategy_name}/scan?demo=0|1

    - demo: optional query flag, default false.
    """
    demo = _parse_bool_query(request.args.get("demo"), default=False)
    out = trigger_strategy_scan_run(strategy_name=strategy_name, demo=demo)
    if not out.get("is_triggered"):
        reason = str(out.get("reason") or "启动扫描失败")
        # Single-flight guard / conflicts return 409 for clearer client handling.
        status = 409 if "运行中" in reason or "扫描任务" in reason else 400
        return error(reason, status)
    return ok({"is_triggered": True, "job_id": out["job_id"], "demo": demo, "strategy_name": strategy_name})


@strategy_scan_api_bp.route(
    "/v1/strategy/<strategy_name>/scan/progress",
    methods=["GET"],
)
def get_strategy_scan_progress(strategy_name: str):
    """GET /v1/strategy/{strategy_name}/scan/progress?job_id=..."""
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    payload = get_scan_progress(strategy_name=strategy_name, job_id=q_job)
    if payload is None:
        return error("任务不存在或与路径不匹配", 404)
    return ok(payload)

