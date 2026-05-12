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
