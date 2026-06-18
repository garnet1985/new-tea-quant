"""Tag console routes — T1-01 … T1-03."""

from flask import Blueprint, request

from core.ui.bff.APIs.strategy_workbench.helpers import pagination_params
from core.ui.bff.shared.response import error, ok

from .tag_stack import get_tag_stack

tag_api_bp = Blueprint("tag_api", __name__)


@tag_api_bp.route("/v1/tags/list", methods=["GET"])
def get_tags_list():
    """GET /v1/tags/list — paginated tag scenario catalog."""
    s = get_tag_stack()
    page, limit = pagination_params()
    items, total = s.fetch_discovered_tags_page(page, limit)
    return ok({"items": items, "total": total, "page": page, "limit": limit})


@tag_api_bp.route("/v1/tag/<path:tag_key>/run", methods=["POST"])
def post_tag_run(tag_key: str):
    """POST /v1/tag/{tag_key}/run — start async tag calculation."""
    s = get_tag_stack()
    out = s.trigger_tag_run(tag_key=tag_key)
    if not out.get("is_triggered"):
        reason = str(out.get("reason") or "启动 Tag 任务失败")
        status = 409 if "运行中" in reason or "进行中" in reason else 400
        return error(reason, status)
    return ok(
        {
            "is_triggered": True,
            "job_id": out["job_id"],
            "run_id": out.get("run_id") or out["job_id"],
            "tag_key": out.get("tag_key") or tag_key,
            "name": out.get("name") or out.get("tag_key") or tag_key,
        }
    )


@tag_api_bp.route("/v1/tag/<path:tag_key>/run/progress", methods=["GET"])
def get_tag_run_progress_route(tag_key: str):
    """GET /v1/tag/{tag_key}/run/progress?job_id=..."""
    s = get_tag_stack()
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    payload = s.get_tag_run_progress(tag_key=tag_key, job_id=q_job)
    if payload is None:
        return error("任务不存在或与路径不匹配", 404)
    return ok(payload)
