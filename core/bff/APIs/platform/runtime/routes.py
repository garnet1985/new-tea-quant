"""Runtime routes — T1-00 pipeline status."""

from flask import Blueprint

from core.infra.task_guard import TaskGuard
from core.bff.shared.response import ok

runtime_api_bp = Blueprint("runtime_api", __name__)


@runtime_api_bp.route("/v1/runtime/pipeline", methods=["GET"])
def get_runtime_pipeline():
    """GET /v1/runtime/pipeline — 长任务忙闲（TaskGuard；路径名历史兼容 FED）。"""
    return ok(TaskGuard.read_status())
