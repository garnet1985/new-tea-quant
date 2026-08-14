from flask import Blueprint

API_VERSION = "v1"
API_NAMESPACE = "strategy"
API_BASE_PATH = f"/{API_VERSION}/{API_NAMESPACE}"

# url_prefix 只在 app 注册时挂 /api；各 route 用 API_BASE_PATH 声明 /v1/strategy/...
strategy_api_bp = Blueprint("strategy_api", __name__)
