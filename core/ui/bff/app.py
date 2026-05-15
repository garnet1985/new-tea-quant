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
from .static_ui import fed_build_ready, register_fed_static_routes, resolve_fed_build_dir

def create_app():
    """创建Flask应用"""
    # 禁用 Flask 默认 ``/static/*``（会抢走 CRA build 里的 ``/static/js|css/...``）
    app = Flask(__name__, static_folder=None, static_url_path=None)
    
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

    # 生产 UI：挂载 ``fed/build``（launcher 默认）；无 build 时保留 JSON 根路径说明
    build_dir = resolve_fed_build_dir()
    if not register_fed_static_routes(app, build_dir=build_dir):
        @app.route('/', methods=['GET'])
        def index():
            build_dir = resolve_fed_build_dir()
            return {
                "message": "BFF API 服务（未挂载前端静态资源）",
                "version": "1.0.0",
                "fed_build": str(build_dir),
                "fed_build_ready": fed_build_ready(build_dir),
                "hint": "在 core/ui/fed 执行 npm run build，或使用 python launcher.py -d 开发模式",
                "endpoints": {
                    "health": "/api/health",
                    "setup_definition": "/api/v1/setup/definition",
                },
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
