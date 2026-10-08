"""Tag visualization routes — T1-07."""

from flask import request

from core.bff.APIs.tag.api_base import tag_api_bp
from core.bff.shared.client_log import log_degraded
from core.bff.shared.response import error, ok

from .implementer import impl as visualization_impl


@tag_api_bp.route("/v1/tag/<path:tag_key>/visualization", methods=["GET"])
def get_tag_visualization(tag_key: str):
    """GET /v1/tag/{tag_key}/visualization?entity_id= — tag value chart payload."""
    api = visualization_impl.lazy_load()
    entity_id = (request.args.get("entity_id") or "").strip()
    try:
        payload = api.fetch(tag_key, entity_id or None)
    except Exception as exc:
        log_degraded("tag.visualization", exc, tag_key)
        return error("读取标签可视化数据失败", 500)
    if payload is None:
        return error("标签不存在", 404)
    return ok(payload)
