"""Agent routes — 产品路径：会话内 run / 清空会话 / 历史。"""

from flask import Blueprint, request

from core.bff.shared.request import json_payload
from core.bff.shared.response import error, ok

from .implementer import impl as agent_impl

agent_api_bp = Blueprint("agent_api", __name__)


@agent_api_bp.route("/v1/agent/quota", methods=["GET"])
def get_agent_quota():
    """GET /v1/agent/quota — 会员猫粮余额（产品 NTQ AI）。"""
    api = agent_impl.lazy_load()
    return ok(api.ntq_quota())


@agent_api_bp.route("/v1/agent/run", methods=["POST"])
def post_agent_run():
    """POST /v1/agent/run — 经 Agent 门控与工具循环处理一句用户消息。"""
    payload = json_payload()
    if not isinstance(payload, dict):
        return error("请求体须为 JSON 对象", 400, code="AGENT_BAD_REQUEST")
    content = str(payload.get("content") or "").strip()
    session_id = str(payload.get("sessionId") or payload.get("session_id") or "").strip() or None
    provider_id = (
        str(payload.get("providerId") or payload.get("provider_id") or "").strip() or None
    )
    api = agent_impl.lazy_load()
    result, err, status = api.run(
        content, session_id=session_id, provider_id=provider_id
    )
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


@agent_api_bp.route("/v1/agent/session/history", methods=["GET", "POST"])
def agent_session_history():
    """GET|POST /v1/agent/session/history — 本机最近对话，供 UI 刷新后恢复。"""
    payload = json_payload()
    session_id = None
    limit = 20
    if isinstance(payload, dict):
        session_id = str(payload.get("sessionId") or payload.get("session_id") or "").strip() or None
        raw_limit = payload.get("limit")
        if raw_limit is not None:
            try:
                limit = max(1, min(40, int(raw_limit)))
            except (TypeError, ValueError):
                limit = 20
    if session_id is None:
        session_id = str(request.args.get("sessionId") or request.args.get("session_id") or "").strip() or None
    raw_q = request.args.get("limit")
    if raw_q is not None:
        try:
            limit = max(1, min(40, int(raw_q)))
        except (TypeError, ValueError):
            pass
    api = agent_impl.lazy_load()
    result, err, status = api.session_history(session_id, limit=limit)
    if err:
        code = "AGENT_UNAVAILABLE" if status >= 500 else "AGENT_BAD_REQUEST"
        return error(err, status, code=code)
    return ok(result)
