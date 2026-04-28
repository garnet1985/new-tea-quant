"""
BFF API 主应用
"""

import os

from flask import Flask
from flask_cors import CORS
from .routes import api_bp

def create_app():
    """创建Flask应用"""
    app = Flask(__name__)
    
    # 启用CORS
    CORS(app)
    
    # 注册蓝图 - 所有API都在 /api 前缀下
    app.register_blueprint(api_bp, url_prefix='/api')
    
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
                "strategies": "/api/v1/strategies",
                "strategies_settings_options_allocation_modes": "/api/v1/strategies/settings-options/allocation-modes",
                "strategies_settings_options_sampling_strategies": "/api/v1/strategies/settings-options/sampling-strategies",
            },
            "docs": "所有API端点都在 /api 前缀下"
        }
    
    return app

if __name__ == "__main__":
    # 默认仅在本机开发环境运行，避免在生产环境暴露 debug 和 0.0.0.0 监听
    app = create_app()

    host = os.getenv("NTQ_BFF_HOST", "127.0.0.1")
    port = int(os.getenv("NTQ_BFF_PORT", "5001"))
    debug = os.getenv("NTQ_BFF_DEBUG", "false").lower() == "true"

    app.run(host=host, port=port, debug=debug, threaded=True)
