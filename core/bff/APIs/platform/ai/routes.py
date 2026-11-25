"""AI 通道 routes — providers 列表与密钥写入（无 chat）。"""

from flask import Blueprint

from core.bff.shared.request import json_payload
from core.bff.shared.response import error, ok

from .helpers import api_key_write_request
from .implementer import impl as ai_impl

ai_api_bp = Blueprint("ai_api", __name__)


@ai_api_bp.route("/v1/ai/providers", methods=["GET"])
def get_ai_providers():
    """GET /v1/ai/providers — 本机已发现的供应商（不含密钥）。"""
    api = ai_impl.lazy_load()
    return ok(api.list_providers())


@ai_api_bp.route("/v1/ai/providers/<provider_id>/api-key", methods=["PUT"])
def put_ai_provider_api_key(provider_id: str):
    """PUT /v1/ai/providers/<id>/api-key — 写入密钥，响应不含明文。"""
    payload = json_payload()
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400, code="AI_BAD_REQUEST")
    api = ai_impl.lazy_load()
    result, err, status = api.set_api_key(provider_id, api_key_write_request(payload))
    if err:
        code = "AI_UNAVAILABLE" if status >= 500 else "AI_BAD_REQUEST"
        return error(err, status, code=code)
    return ok(result)
