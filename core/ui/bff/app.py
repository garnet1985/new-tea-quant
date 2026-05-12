"""
BFF API 主应用
"""

from flask import Flask
from flask_cors import CORS
from .APIs.health import health_api_bp
from .APIs.setup import setup_api_bp
from .APIs.strategy_workbench import strategy_workbench_api_bp
from .APIs.strategy_scan import strategy_scan_api_bp
from .APIs.settings import settings_api_bp
from .conf import conf

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    
    # 启用CORS
    CORS(
        app,
        origins=conf["CORS_ALLOW_ORIGINS"],
        methods=conf["CORS_ALLOW_METHODS"],
        allow_headers=conf["CORS_ALLOW_HEADERS"],
        supports_credentials=bool(conf["CORS_ALLOW_CREDENTIALS"]),
        max_age=int(conf["CORS_MAX_AGE"]),
    )
    
    # 注册蓝图 - 所有API都在 /api 前缀下
    app.register_blueprint(health_api_bp, url_prefix='/api')
    app.register_blueprint(setup_api_bp, url_prefix='/api')
    app.register_blueprint(strategy_workbench_api_bp, url_prefix='/api')
    app.register_blueprint(strategy_scan_api_bp, url_prefix='/api')
    app.register_blueprint(settings_api_bp, url_prefix='/api')
    
    # 添加根路径重定向到API文档
    @app.route('/', methods=['GET'])
    def index():
        """API根路径"""
        return {
            "message": "BFF API 服务",
            "version": "1.0.0",
            "endpoints": {
                "health": "/api/health",
                "setup_definition": "/api/v1/setup/definition",
                "setup_status": "/api/v1/setup/status",
                "setup_start": "/api/v1/setup/start",
                "strategy_workbench_v2": "见 core/ui/fed/.../strategyWorkbenchPage/API.md（前缀 /api）",
            },
            "docs": "所有API端点都在 /api 前缀下"
        }
    
    return app

if __name__ == "__main__":
    # 启动参数统一读取 core/ui/bff/conf.py
    app = create_app()

    host = str(conf["HOST"])
    port = int(conf["PORT"])
    debug = bool(conf["DEBUG"])

    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=bool(conf.get("THREADED", False)),
    )
