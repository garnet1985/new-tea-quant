"""HTTP / request helpers for strategy workbench BFF routes."""

from flask import request

from core.ui.bff.shared.response import error


def pagination_params(*, default_limit: int = 20, max_limit: int = 100) -> tuple[int, int]:
    """Parse ``page`` / ``limit`` query params (1-based page)."""
    raw_page = request.args.get("page", "1")
    raw_limit = request.args.get("limit", str(default_limit))
    try:
        page = int(raw_page)
    except ValueError:
        page = 1
    try:
        limit = int(raw_limit)
    except ValueError:
        limit = default_limit
    page = max(1, page)
    limit = max(1, min(limit, max_limit))
    return page, limit


def json_payload() -> dict:
    """Parse JSON body; missing or invalid becomes ``{}``."""
    return request.get_json(silent=True) or {}


def v2_not_implemented(code: str):
    """Placeholder response until a route delegates to the backend."""
    return error(f"{code} 未实现（BFF 仅占位）", 501)
