"""
BFF API 路由定义
"""

from flask import Blueprint, request, jsonify
from .api import BFFApi

# 创建蓝图
api_bp = Blueprint('api', __name__)
bff_api = BFFApi()

@api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return bff_api.health_check()

@api_bp.route('/stock/kline/<stock_id>/<term>', methods=['GET'])
def get_stock_kline(stock_id, term):
    """获取股票K线数据"""
    return bff_api.get_stock_kline(stock_id, term)

@api_bp.route('/stock/scan/<strategy>/<stock_id>', methods=['GET'])
def get_stock_scan(strategy, stock_id):
    """获取股票策略扫描结果"""
    return bff_api.get_stock_scan(strategy, stock_id)

@api_bp.route('/stock/simulate/<strategy>/<stock_id>', methods=['GET'])
def get_stock_simulate(strategy, stock_id):
    """获取股票策略模拟结果"""
    return bff_api.get_stock_simulate(strategy, stock_id)

@api_bp.route('/stock/hl-analysis/<stock_id>', methods=['GET'])
def get_stock_hl_analysis(stock_id):
    """获取股票HL策略分析结果"""
    return bff_api.get_stock_hl_analysis(stock_id)
