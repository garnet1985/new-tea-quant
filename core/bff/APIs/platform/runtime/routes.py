"""Runtime routes — T1-00 pipeline / running + pending jobs."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from flask import Blueprint

from core.bff.shared.response import error, ok
from core.infra.job_pipeline import JobPipeline

runtime_api_bp = Blueprint("runtime_api", __name__)


def _pipeline_message(
    job: Optional[Dict[str, Any]],
    jobs: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """``job`` = running；``jobs`` = running + pending。保留 ``busy`` 兼容旧 FED。"""
    job_list = [dict(row) for row in (jobs or []) if isinstance(row, dict)]
    pending = [
        row for row in job_list
        if str(row.get("status") or "").strip().lower() == "pending"
    ]
    if not job:
        return {
            "busy": False,
            "job": None,
            "jobs": job_list,
            "pending": pending,
            "pending_count": len(pending),
            "kind": None,
            "job_id": None,
            "resource_key": None,
            "label": None,
            "domains": [],
            "started_at": None,
            "status": None,
            "progress": None,
        }
    return {
        "busy": True,
        "job": dict(job),
        "jobs": job_list,
        "pending": pending,
        "pending_count": len(pending),
        "kind": job.get("kind"),
        "job_id": job.get("job_id"),
        "resource_key": job.get("resource_key"),
        "label": job.get("label"),
        "domains": list(job.get("domains") or []),
        "started_at": job.get("started_at"),
        "status": job.get("status"),
        "progress": job.get("progress"),
    }


@runtime_api_bp.route("/v1/runtime/pipeline", methods=["GET"])
def get_runtime_pipeline():
    """GET /v1/runtime/pipeline — JobPipeline 任务表（running + pending）。"""
    return ok(
        _pipeline_message(
            JobPipeline.get_running_job(),
            JobPipeline.list_jobs(),
        )
    )


@runtime_api_bp.route("/v1/runtime/pipeline/jobs/<path:job_id>", methods=["DELETE"])
def delete_runtime_pipeline_job(job_id: str):
    """DELETE /v1/runtime/pipeline/jobs/:job_id — 取消 pending。"""
    out = JobPipeline.cancel(job_id)
    if not out.get("cancelled"):
        return error(str(out.get("reason") or "取消失败"), 400)
    return ok(
        {
            **out,
            **_pipeline_message(
                JobPipeline.get_running_job(),
                JobPipeline.list_jobs(),
            ),
        }
    )
