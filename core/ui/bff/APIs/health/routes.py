"""Health routes (endpoint + logic)."""

from flask import Blueprint, jsonify

health_api_bp = Blueprint("health_api", __name__)


@health_api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        "success": True,
        "message": "BFF API 运行正常",
        "timestamp": "当前时间"
    })
