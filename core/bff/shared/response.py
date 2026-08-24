"""Shared response helpers for BFF APIs."""

from flask import jsonify
from typing import Optional


def ok(message: dict, http_status: int = 200):
    """Return a standard ok response."""
    return jsonify({"status": "ok", "message": message}), http_status


def error(detail: str, http_status: int = 500, code: Optional[str] = None):
    """Return a standard error response."""
    payload = {"detail": detail}
    if code:
        payload["code"] = code
    return jsonify({"status": "error", "message": payload}), http_status


def passthrough(payload: dict, http_status: int = 200):
    """Return an already-structured payload as JSON response."""
    return jsonify(payload), http_status


def from_payload(payload: dict, *, error_http_status: int = 400):
    """
    Map internal ``{status, message}`` dict to Flask response.

    Runtime helpers (e.g. setup) may return ``status: error`` with HTTP 200;
    this converts them to proper error responses for the frontend request layer.
    """
    if isinstance(payload, dict) and payload.get("status") == "error":
        msg = payload.get("message")
        if isinstance(msg, dict):
            return error(
                str(msg.get("detail") or "操作失败"),
                error_http_status,
                msg.get("code"),
            )
        return error(str(msg or "操作失败"), error_http_status)
    return passthrough(payload)
