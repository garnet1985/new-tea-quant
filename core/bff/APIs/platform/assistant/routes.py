"""Assistant routes — providers 列表、密钥写入与一轮聊天。"""

from flask import Blueprint

from core.bff.shared.request import json_payload
from core.bff.shared.response import error, ok

from .helpers import api_key_write_request, chat_request
from .implementer import impl as assistant_impl

assistant_api_bp = Blueprint("assistant_api", __name__)


@assistant_api_bp.route("/v1/assistant/providers", methods=["GET"])
def get_assistant_providers():
    """GET /v1/assistant/providers — 本机已发现的供应商（不含密钥）。"""
    api = assistant_impl.lazy_load()
    return ok(api.list_providers())


@assistant_api_bp.route("/v1/assistant/chat", methods=["POST"])
def post_assistant_chat():
    """POST /v1/assistant/chat — 发送一句用户消息。"""
    payload = json_payload()
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400, code="ASSISTANT_BAD_REQUEST")
    body = chat_request(payload)
    api = assistant_impl.lazy_load()
    result, err, status = api.chat(
        body["content"], body["provider_id"], body.get("history")
    )
    if err:
        code = "ASSISTANT_UNAVAILABLE" if status >= 500 else "ASSISTANT_BAD_REQUEST"
        return error(err, status, code=code)
    return ok(result)


@assistant_api_bp.route("/v1/assistant/providers/<provider_id>/api-key", methods=["PUT"])
def put_assistant_provider_api_key(provider_id: str):
    """PUT /v1/assistant/providers/<id>/api-key — 写入密钥，响应不含明文。"""
    payload = json_payload()
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400, code="ASSISTANT_BAD_REQUEST")
    api = assistant_impl.lazy_load()
    result, err, status = api.set_api_key(provider_id, api_key_write_request(payload))
    if err:
        code = "ASSISTANT_UNAVAILABLE" if status >= 500 else "ASSISTANT_BAD_REQUEST"
        return error(err, status, code=code)
    return ok(result)
