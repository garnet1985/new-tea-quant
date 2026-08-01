"""Tag runner routes — T1-02 / T1-03."""

from flask import request

from core.bff.APIs.tag.api_base import tag_api_bp
from core.bff.shared.response import error, ok

from .implementer import impl as runner_impl


@tag_api_bp.route("/v1/tag/<path:tag_key>/run", methods=["POST"])
def post_tag_run(tag_key: str):
    """POST /v1/tag/{tag_key}/run — start async tag calculation."""
    api = runner_impl.lazy_load()
    out = api.trigger_run(tag_key=tag_key)
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
    api = runner_impl.lazy_load()
    q_job = (request.args.get("job_id") or "").strip()
    if not q_job:
        return error("缺少必填 query 参数 job_id", 400)
    payload = api.get_progress(tag_key=tag_key, job_id=q_job)
    if payload is None:
        return error("任务不存在或与路径不匹配", 404)
    return ok(payload)
