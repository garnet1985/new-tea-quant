"""Runtime routes — T1-00 pipeline status."""

from flask import Blueprint

from core.infra.system_actions import SystemActions
from core.bff.shared.response import ok

runtime_api_bp = Blueprint("runtime_api", __name__)


@runtime_api_bp.route("/v1/runtime/pipeline", methods=["GET"])
def get_runtime_pipeline():
    """GET /v1/runtime/pipeline — global DuckDB pipeline lease."""
    return ok(SystemActions.pipeline.read_status())
