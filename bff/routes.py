"""
BFF API 路由定义
"""

from flask import Blueprint, request, jsonify
from .api import BFFApi

# 创建蓝图
api_bp = Blueprint('api', __name__)
# 延迟初始化，避免在模块导入时创建实例
bff_api = None

def get_bff_api():
    """获取BFF API实例，延迟初始化"""
    global bff_api
    if bff_api is None:
        bff_api = BFFApi()
    return bff_api

@api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return get_bff_api().health_check()

@api_bp.route('/stock/kline/<stock_id>/<term>', methods=['GET'])
def get_stock_kline(stock_id, term):
    """获取股票K线数据"""
    return get_bff_api().get_stock_kline(stock_id, term)

@api_bp.route('/stock/scan/<strategy>/<stock_id>', methods=['GET'])
def get_stock_scan(strategy, stock_id):
    """获取股票策略扫描结果"""
    return get_bff_api().get_stock_scan(strategy, stock_id)

@api_bp.route('/stock/simulate/<strategy>/<stock_id>', methods=['GET'])
def get_stock_simulate(strategy, stock_id):
    """获取股票策略模拟结果"""
    return get_bff_api().get_stock_simulate(strategy, stock_id)

@api_bp.route('/stock/hl-analysis/<stock_id>', methods=['GET'])
def get_stock_hl_analysis(stock_id):
    """获取股票HL策略分析结果"""
    return get_bff_api().get_stock_hl_analysis(stock_id)

@api_bp.route('/stock/all-historic-lows/<stock_id>', methods=['GET'])
def get_stock_all_historic_lows(stock_id):
    """获取股票所有计算出的历史低点"""
    return get_bff_api().get_stock_all_historic_lows(stock_id)

# ==================== 投资跟踪 API ====================

@api_bp.route('/investment/trades', methods=['GET'])
def get_all_open_trades():
    """获取所有正在进行中的交易（复数）"""
    return get_bff_api().get_all_open_trades()

@api_bp.route('/investment/trades/history', methods=['GET'])
def get_all_closed_trades():
    """获取所有已关闭的交易（历史记录）"""
    return get_bff_api().get_all_closed_trades()

@api_bp.route('/investment/trades/<int:trade_id>', methods=['GET'])
def get_trade_detail(trade_id):
    """获取单个交易详情"""
    return get_bff_api().get_trade_detail(trade_id)

@api_bp.route('/investment/trades/<int:trade_id>/operations', methods=['GET'])
def get_trade_operations(trade_id):
    """获取某个交易的所有操作记录（复数）"""
    return get_bff_api().get_trade_operations(trade_id)

@api_bp.route('/investment/trades', methods=['POST'])
def create_trade():
    """创建一笔交易（单数操作，复数路径）"""
    data = request.get_json()
    return get_bff_api().create_trade(data)

@api_bp.route('/investment/trades/<int:trade_id>/operations', methods=['POST'])
def create_operation(trade_id):
    """创建一笔操作（单数操作，复数路径）"""
    data = request.get_json()
    return get_bff_api().create_operation(trade_id, data)

@api_bp.route('/investment/strategies', methods=['GET'])
def get_strategies_list():
    """获取可用策略列表"""
    return get_bff_api().get_strategies_list()

@api_bp.route('/investment/stocks/search/<keyword>', methods=['GET'])
def search_stocks(keyword):
    """搜索股票（用于自动完成）"""
    return get_bff_api().search_stocks(keyword)

@api_bp.route('/investment/trades/<int:trade_id>', methods=['PUT'])
def update_trade(trade_id):
    """更新一笔交易"""
    data = request.get_json()
    return get_bff_api().update_trade(trade_id, data)

@api_bp.route('/investment/trades/<int:trade_id>', methods=['DELETE'])
def delete_trade(trade_id):
    """删除一笔交易"""
    return get_bff_api().delete_trade(trade_id)

@api_bp.route('/investment/trades/<int:trade_id>/operations/<int:operation_id>', methods=['PUT'])
def update_operation(trade_id, operation_id):
    """更新一笔操作"""
    data = request.get_json()
    return get_bff_api().update_operation(trade_id, operation_id, data)

@api_bp.route('/investment/trades/<int:trade_id>/operations/<int:operation_id>', methods=['DELETE'])
def delete_operation(trade_id, operation_id):
    """删除一笔操作"""
    return get_bff_api().delete_operation(trade_id, operation_id)
