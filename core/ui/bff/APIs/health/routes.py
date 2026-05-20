"""Health routes (endpoint + logic)."""

from core.system import get_version
from core.ui.bff.shared.response import ok
from flask import Blueprint

health_api_bp = Blueprint("health_api", __name__)


@health_api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查；``message.version`` 与 ``core/system.json`` / ``get_version()`` 一致。"""
    return ok({
        "healthy": True,
        "version": get_version(),
    })
