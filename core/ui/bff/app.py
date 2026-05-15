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
from .static_ui import (
    fed_build_ready,
    fed_build_static_dir,
    register_fed_static_routes,
    resolve_fed_build_dir,
)


def create_app():
    build_dir = resolve_fed_build_dir()
    static_folder = None
    static_url_path = None
    if fed_build_ready(build_dir):
        static_root = fed_build_static_dir(build_dir).resolve()
        if static_root.is_dir():
            static_folder = str(static_root)
            static_url_path = "/static"

    app = Flask(__name__, static_folder=static_folder, static_url_path=static_url_path)

    CORS(
        app,
        origins=conf["CORS_ALLOW_ORIGINS"],
        methods=conf["CORS_ALLOW_METHODS"],
        allow_headers=conf["CORS_ALLOW_HEADERS"],
        supports_credentials=bool(conf["CORS_ALLOW_CREDENTIALS"]),
        max_age=int(conf["CORS_MAX_AGE"]),
    )

    app.register_blueprint(health_api_bp, url_prefix="/api")
    app.register_blueprint(setup_api_bp, url_prefix="/api")
    app.register_blueprint(strategy_workbench_api_bp, url_prefix="/api")
    app.register_blueprint(strategy_scan_api_bp, url_prefix="/api")
    app.register_blueprint(settings_api_bp, url_prefix="/api")

    if not register_fed_static_routes(app, build_dir=build_dir):

        @app.route("/", methods=["GET"])
        def index():
            return {
                "message": "BFF API（未挂载 fed/build）",
                "fed_build": str(build_dir),
                "fed_build_ready": fed_build_ready(build_dir),
                "hint": "npm run build（core/ui/fed）或 python launcher.py -d",
                "endpoints": {"health": "/api/health"},
            }

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(
        host=str(conf["HOST"]),
        port=int(conf["PORT"]),
        debug=bool(conf["DEBUG"]),
        threaded=bool(conf.get("THREADED", False)),
    )
