"""
BFF API 主应用
"""

import atexit

from flask import Flask
from flask_cors import CORS
from .APIs.platform import (
    health_api_bp,
    runtime_api_bp,
    setup_api_bp,
    settings_api_bp,
)
from .APIs.data import data_contract_api_bp, data_source_api_bp
from .APIs.strategy import strategy_api_bp
from .APIs.tag import tag_api_bp
from .conf import conf
from .static_ui import (
    fed_build_ready,
    fed_build_static_dir,
    register_fed_static_routes,
    resolve_fed_build_dir,
    should_mount_fed_build,
)


def create_app():
    build_dir = resolve_fed_build_dir()
    static_folder = None
    static_url_path = None
    if should_mount_fed_build() and fed_build_ready(build_dir):
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
    app.register_blueprint(strategy_api_bp, url_prefix="/api")
    app.register_blueprint(settings_api_bp, url_prefix="/api")
    app.register_blueprint(runtime_api_bp, url_prefix="/api")
    app.register_blueprint(data_contract_api_bp, url_prefix="/api")
    app.register_blueprint(data_source_api_bp, url_prefix="/api")
    app.register_blueprint(tag_api_bp, url_prefix="/api")

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


def _shutdown_worker_children() -> None:
    try:
        from core.ui.process_cleanup import terminate_multiprocessing_children

        terminate_multiprocessing_children()
    except Exception:
        pass


def _register_shutdown_hooks() -> None:
    atexit.register(_shutdown_worker_children)


def _start_trace_drain() -> None:
    """Lazy-start usage trace background drain (must not be a top-level import)."""
    try:
        from core.infra.trace import Trace

        Trace.start_background_drain()
    except Exception:
        pass


if __name__ == "__main__":
    _register_shutdown_hooks()
    app = create_app()
    _start_trace_drain()
    app.run(
        host=str(conf["HOST"]),
        port=int(conf["PORT"]),
        debug=bool(conf["DEBUG"]),
        threaded=bool(conf.get("THREADED", False)),
    )
