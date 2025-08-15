"""
BFF API 主应用
"""

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
                "stock_kline": "/api/stock/kline/<stock_id>/<term>",
                "stock_simulate": "/api/stock/simulate/<strategy>/<stock_id>",
                "stock_scan": "/api/stock/scan/<strategy>/<stock_id>"
            },
            "docs": "所有API端点都在 /api 前缀下"
        }
    
    return app
