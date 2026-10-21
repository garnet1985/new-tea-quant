"""Series relation run / results routes."""

from flask import request

from core.bff.APIs.series_relation.api_base import series_relation_api_bp
from core.bff.shared.response import error, ok

from .runner_implementer import runner_impl


@series_relation_api_bp.route(
    "/v1/series-relations/<path:key>/run", methods=["POST"]
)
def post_series_relation_run(key: str):
    """POST /v1/series-relations/<key>/run"""
    api = runner_impl.lazy_load()
    payload = api.run_scene(key)
    if not payload.get("success"):
        return error(
            str(payload.get("error") or "跑批失败"),
            http_status=400,
            extra={"key": payload.get("key")},
        )
    return ok(payload)


@series_relation_api_bp.route(
    "/v1/series-relations/<path:key>/results", methods=["GET"]
)
def get_series_relation_results(key: str):
    """GET /v1/series-relations/<key>/results"""
    api = runner_impl.lazy_load()
    try:
        max_points = int(request.args.get("max_points") or 800)
    except (TypeError, ValueError):
        max_points = 800
    payload = api.get_results(key, max_points=max_points)
    if not payload.get("success"):
        return error(str(payload.get("error") or "读取失败"), http_status=404)
    return ok(payload)
