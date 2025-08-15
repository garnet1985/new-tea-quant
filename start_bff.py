#!/usr/bin/env python3
"""
BFF API 启动脚本
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bff.app import create_app
from loguru import logger

if __name__ == '__main__':
    logger.info("🚀 启动BFF API服务...")
    logger.info("📡 服务地址: http://localhost:5001")
    logger.info("🔍 健康检查: http://localhost:5001/api/health")
    logger.info("📊 股票K线: http://localhost:5001/api/stock/kline/000002.SZ/daily")
    logger.info("🎯 策略扫描: http://localhost:5001/api/stock/scan/historicLow/000002.SZ")
    logger.info("📈 策略模拟: http://localhost:5001/api/stock/simulate/historicLow/000002.SZ")
    logger.info("📖 API文档: http://localhost:5001/")
    
    try:
        app = create_app()
        app.run(host='0.0.0.0', port=5001, debug=True)
    except KeyboardInterrupt:
        logger.info("🛑 BFF API服务已停止")
    except Exception as e:
        logger.error(f"❌ BFF API服务启动失败: {e}")
