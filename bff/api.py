"""
BFF API 统一入口
按业务模块拆分，通过这里统一暴露
"""
import sys
import os
from flask import jsonify
from loguru import logger

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from bff.APIs.stock_api import StockApi
from bff.APIs.investment_api import InvestmentApi


class BFFApi:
    """BFF API 统一入口类"""
    
    def __init__(self):
        """初始化BFF API"""
        from utils.db.db_manager import DatabaseManager
        
        # 在顶层初始化数据库管理器
        self.db_manager = DatabaseManager()
        self.db_manager.initialize()
        
        # 初始化业务API，传入db_manager
        self._stock_api = None
        self._investment_api = None
    
    @property
    def stock_api(self):
        """股票API（延迟初始化）"""
        if self._stock_api is None:
            self._stock_api = StockApi(db_manager=self.db_manager)
        return self._stock_api
    
    @property
    def investment_api(self):
        """投资API（延迟初始化）"""
        if self._investment_api is None:
            self._investment_api = InvestmentApi(db_manager=self.db_manager)
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
        """获取股票的HL策略分析结果"""
        return self.stock_api.get_stock_hl_analysis(stock_id)
    
    def get_stock_all_historic_lows(self, stock_id: str):
        """获取股票所有计算出的历史低点"""
        return self.stock_api.get_stock_all_historic_lows(stock_id)
    
    # ==================== 投资跟踪 API ====================
    
    def get_trade_detail(self, trade_id: int):
        """获取单个交易详情"""
        return self.investment_api.get_trade_detail(trade_id)
    
    def get_all_open_trades(self):
        """获取所有正在进行中的交易"""
        return self.investment_api.get_all_open_trades()
    
    def get_trade_operations(self, trade_id: int):
        """根据trade_id获取所有操作记录"""
        return self.investment_api.get_trade_operations(trade_id)
    
    def create_trade(self, data: dict):
        """创建一笔交易"""
        return self.investment_api.create_trade(data)
    
    def create_operation(self, trade_id: int, data: dict):
        """创建一笔操作（买入/卖出/补仓）"""
        return self.investment_api.create_operation(trade_id, data)
    
    def update_trade(self, trade_id: int, data: dict):
        """更新一笔交易"""
        return self.investment_api.update_trade(trade_id, data)
    
    def delete_trade(self, trade_id: int):
        """删除一笔交易"""
        return self.investment_api.delete_trade(trade_id)
    
    def update_operation(self, trade_id: int, operation_id: int, data: dict):
        """更新一笔操作（买入/卖出）"""
        return self.investment_api.update_operation(trade_id, operation_id, data)
    
    def delete_operation(self, trade_id: int, operation_id: int):
        """删除一笔操作（买入/卖出）"""
        return self.investment_api.delete_operation(trade_id, operation_id)
    
    def get_strategies_list(self):
        """获取可用策略列表"""
        return self.investment_api.get_strategies_list()
    
    def search_stocks(self, keyword: str):
        """搜索股票（用于自动完成）"""
        return self.investment_api.search_stocks(keyword)
