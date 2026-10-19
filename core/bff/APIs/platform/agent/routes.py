"""Agent routes — 产品路径：会话内 run / 清空会话。"""

from flask import Blueprint

from core.bff.shared.request import json_payload
from core.bff.shared.response import error, ok

from .implementer import impl as agent_impl

agent_api_bp = Blueprint("agent_api", __name__)


@agent_api_bp.route("/v1/agent/run", methods=["POST"])
def post_agent_run():
    """POST /v1/agent/run — 经 Agent 门控与工具循环处理一句用户消息。"""
    payload = json_payload()
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400, code="AGENT_BAD_REQUEST")
    content = str(payload.get("content") or "").strip()
    session_id = str(payload.get("sessionId") or payload.get("session_id") or "").strip() or None
    api = agent_impl.lazy_load()
    result, err, status = api.run(content, session_id=session_id)
    if err:
        code = "AGENT_UNAVAILABLE" if status >= 500 else "AGENT_BAD_REQUEST"
        if status == 429:
            code = "AGENT_QUOTA"
        elif status == 401:
            code = "AGENT_UNAUTHORIZED"
        return error(err, status, code=code)
    return ok(result)


@agent_api_bp.route("/v1/agent/session/clear", methods=["POST"])
def post_agent_session_clear():
    """POST /v1/agent/session/clear — 清空本机会话对话与局部状态。"""
    payload = json_payload()
    session_id = None
    if isinstance(payload, dict):
        session_id = str(payload.get("sessionId") or payload.get("session_id") or "").strip() or None
    api = agent_impl.lazy_load()
    result, err, status = api.clear_session(session_id)
    if err:
        code = "AGENT_UNAVAILABLE" if status >= 500 else "AGENT_BAD_REQUEST"
        return error(err, status, code=code)
    return ok(result)
