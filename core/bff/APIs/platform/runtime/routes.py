"""Runtime routes — T1-00 pipeline / running job."""

from __future__ import annotations

from typing import Any, Dict, Optional

from flask import Blueprint

from core.bff.shared.response import ok
from core.infra.job_pipeline import JobPipeline

runtime_api_bp = Blueprint("runtime_api", __name__)


def _pipeline_message(job: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """统一读面：``job`` 为主；保留 ``busy`` 等扁平字段兼容现有 FED。"""
    if not job:
        return {
            "busy": False,
            "job": None,
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
    """GET /v1/runtime/pipeline — 当前 running 长任务（JobPipeline；路径名历史兼容）。"""
    return ok(_pipeline_message(JobPipeline.get_running_job()))
