"""BFF API 统一入口。"""

from flask import jsonify

from .APIs.stock_api import StockApi
from .APIs.investment_api import InvestmentApi
from core.modules.data_manager import DataManager


class BFFApi:
    """BFF API 统一入口类"""
    
    def __init__(self):
        """初始化 BFF API。"""
        # 使用全局 DataManager 单例（内部会管理 DatabaseManager）
        self.data_mgr = DataManager(is_verbose=False)
        
        # 初始化业务API（惰性创建）
        self._stock_api = None
        self._investment_api = None
    
    @property
    def stock_api(self):
        """股票API（延迟初始化）"""
        if self._stock_api is None:
            self._stock_api = StockApi(data_mgr=self.data_mgr)
        return self._stock_api
    
    @property
    def investment_api(self):
        """投资API（延迟初始化）"""
        if self._investment_api is None:
            # InvestmentApi 依赖 DataManager；这里与 stock_api 共享同一实例。
            self._investment_api = InvestmentApi(data_mgr=self.data_mgr)
        return self._investment_api
    
    # ==================== 健康检查 ====================
    
    def health_check(self):
        """健康检查"""
        return jsonify({
            "success": True,
            "message": "BFF API 运行正常",
            "timestamp": "当前时间"
        })
    
    # ==================== 股票相关 API ====================
    
    def get_stock_kline(self, stock_id: str, term: str = 'daily'):
        """获取股票K线数据"""
        return self.stock_api.get_stock_kline(stock_id, term)
    
    def get_stock_scan(self, strategy: str, stock_id: str):
        """获取股票策略扫描结果"""
        return self.stock_api.get_stock_scan(strategy, stock_id)
    
    def get_stock_simulate(self, strategy: str, stock_id: str):
        """获取股票策略模拟结果"""
        return self.stock_api.get_stock_simulate(strategy, stock_id)

    def get_stock_hl_analysis(self, stock_id: str):
        """获取股票 HL 策略分析结果。"""
        return self.stock_api.get_stock_hl_analysis(stock_id)

    def get_stock_all_historic_lows(self, stock_id: str):
        """获取股票所有历史低点。"""
        return self.stock_api.get_stock_all_historic_lows(stock_id)
    
    # ==================== 投资相关 API ====================
    
    def get_all_closed_trades(self):
        """获取所有已关闭的交易"""
        return self.investment_api.get_all_closed_trades()

    def get_all_open_trades(self):
        """获取所有进行中的交易。"""
        return self.investment_api.get_all_open_trades()
    
    def get_open_positions(self):
        """获取当前持仓（兼容旧方法，转发到 open trades）。"""
        return self.investment_api.get_all_open_trades()
    
    def get_trades_by_stock(self, stock_id: str):
        """按股票获取交易记录"""
        return self.investment_api.get_trades_by_stock(stock_id)
    
    def get_investment_overview(self):
        """获取投资概览（当前 BFF 未提供专用聚合，先返回 open trades）。"""
        return self.investment_api.get_all_open_trades()

    def get_trade_detail(self, trade_id: int):
        """获取单笔交易详情。"""
        return self.investment_api.get_trade_detail(trade_id)

    def get_trade_operations(self, trade_id: int):
        """获取交易操作列表。"""
        return self.investment_api.get_trade_operations(trade_id)

    def create_trade(self, data: dict):
        """创建交易。"""
        return self.investment_api.create_trade(data)

    def create_operation(self, trade_id: int, data: dict):
        """创建交易操作。"""
        return self.investment_api.create_operation(trade_id, data)

    def get_strategies_list(self):
        """获取策略列表。"""
        return self.investment_api.get_strategies_list()

    def search_stocks(self, keyword: str):
        """搜索股票（自动完成）。"""
        return self.investment_api.search_stocks(keyword)

    def update_trade(self, trade_id: int, data: dict):
        """更新交易。"""
        return self.investment_api.update_trade(trade_id, data)

    def delete_trade(self, trade_id: int):
        """删除交易。"""
        return self.investment_api.delete_trade(trade_id)

    def update_operation(self, trade_id: int, operation_id: int, data: dict):
        """更新交易操作。"""
        return self.investment_api.update_operation(trade_id, operation_id, data)

    def delete_operation(self, trade_id: int, operation_id: int):
        """删除交易操作。"""
        return self.investment_api.delete_operation(trade_id, operation_id)


