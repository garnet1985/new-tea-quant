"""Runtime routes — T1-00 pipeline status."""

from flask import Blueprint

from core.infra.system_actions.cache_cleanup.pipeline_lease import read_pipeline_status
from core.bff.shared.response import ok

runtime_api_bp = Blueprint("runtime_api", __name__)


@runtime_api_bp.route("/v1/runtime/pipeline", methods=["GET"])
def get_runtime_pipeline():
    """GET /v1/runtime/pipeline — global DuckDB pipeline lease."""
    return ok(read_pipeline_status())
