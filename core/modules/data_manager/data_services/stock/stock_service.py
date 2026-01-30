"""
股票数据服务（StockService）

职责：
1. 提供单个股票的基础信息查询
2. 提供跨表查询（组合多个表的数据）
3. 作为子服务的入口，提供子服务属性访问

涉及的表：
- stock_list: 股票列表

子服务：
- list: 股票列表服务（data_mgr.stock.list.load()）
- kline: K线数据服务（data_mgr.stock.kline.load_qfq()）
- tags: 标签数据服务（data_mgr.stock.tags.load_scenario()）
- corporate_finance: 财务数据服务（data_mgr.stock.corporate_finance.load()）

使用示例：
    # 单个股票信息
    stock_info = data_mgr.stock.load_info('000001.SZ')
    
    # 股票列表（通过 list 服务）
    stock_list = data_mgr.stock.list.load(filtered=True)
    all_stocks = data_mgr.stock.list.load_all()
    
    # 跨表查询
    stock_with_price = data_mgr.stock.load_with_latest_price('000001.SZ')
"""
from typing import List, Dict, Any, Optional
from loguru import logger

from .. import BaseDataService


class StockService(BaseDataService):
    """股票数据服务（统一入口）"""
    
    def __init__(self, data_manager: Any):
        """
        初始化股票数据服务
        
        Args:
            data_manager: DataManager 实例
        """
        super().__init__(data_manager)
        
        # 初始化子服务（从 sub_services 目录导入）
        from .sub_services import ListService, KlineService, TagDataService, CorporateFinanceService
        
        self.list = ListService(data_manager)
        self.kline = KlineService(data_manager)
        self.tags = TagDataService(data_manager)
        self.corporate_finance = CorporateFinanceService(data_manager)
        
        # 获取相关 Model（表名来自 core.tables，DataManager 为 driver）
        from core.tables import SYS_STOCK_LIST
        self._stock_list = data_manager.get_table(SYS_STOCK_LIST)
        
        # 获取 DatabaseManager 用于复杂 SQL 查询
        from core.infra.db import DatabaseManager
        self.db = DatabaseManager.get_default(auto_init=True)
    
    # ==================== 股票基础信息 ====================

    def load_info(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        加载股票基本信息
        
        Args:
            stock_id: 股票代码
            
        Returns:
            Optional[Dict[str, Any]]: 股票信息字典，如果不存在返回 None
        """
        return self._stock_list.load_one("id = %s", (stock_id,))
    
    # ==================== 跨表查询 ====================
    
    def load_with_latest_price(self, stock_id: str) -> Optional[Dict[str, Any]]:
        """
        获取股票基本信息和最新价格（使用 JOIN 优化）
        
        跨表业务方法，组合stock_list和stock_kline的数据
        
        Args:
            stock_id: 股票ID
            
        Returns:
            Dict: {
                'id': 股票ID,
                'name': 股票名称,
                'industry': 行业,
                'current_price': 最新收盘价,
                'current_price_date': 最新价格日期,
                'market_cap': 市值,
                'pe': PE,
                'pb': PB,
                'total_share': 总股本,
                'float_share': 流通股本,
                'turnover_vol': 成交量,
                'turnover_value': 成交额,
                'turnover_rate': 换手率,
                'high': 最高价,
                'low': 最低价,
                'open': 开盘价,
                'close': 收盘价,
                ...
            }
        """
        # 使用 JOIN 一次查询出股票信息和最新K线数据
        sql = """
        SELECT 
            s.*,
            k.date as kline_date,
            k.open, k.high, k.low, k.close, k.volume, k.amount,
            k.total_market_value, k.pe, k.pb, k.total_share, k.float_share,
            k.turnover_rate, k.highest, k.lowest
        FROM stock_list s
        LEFT JOIN stock_kline k ON (
            s.id = k.id 
            AND k.term = 'daily'
            AND k.date = (
                SELECT MAX(k2.date)
                FROM stock_kline k2
                WHERE k2.id = s.id AND k2.term = 'daily'
            )
        )
        WHERE s.id = %s
        LIMIT 1
        """
        
        try:
            results = self.db.execute_sync_query(sql, (stock_id,))
            if not results:
                return None
            
            row = results[0]
            result = {
                'id': row.get('id'),
                'name': row.get('name'),
                'industry': row.get('industry'),
            }
            
            # 如果有K线数据，添加价格相关字段
            if row.get('kline_date'):
                result.update({
                    'current_price': row.get('close'),
                    'current_price_date': row.get('kline_date'),
                    'market_cap': row.get('total_market_value'),
                    'pe': row.get('pe'),
                    'pb': row.get('pb'),
                    'total_share': row.get('total_share'),
                    'float_share': row.get('float_share'),
                    'turnover_vol': row.get('volume'),
                    'turnover_value': row.get('amount'),
                    'turnover_rate': row.get('turnover_rate'),
                    'high': row.get('highest'),
                    'low': row.get('lowest'),
                    'open': row.get('open'),
                    'close': row.get('close'),
                })
            
            return result
            
        except Exception as e:
            logger.error(f"查询股票信息和最新价格失败: {e}")
            # 回退到原来的多次查询方式
            stock_info = self.load_info(stock_id)
            if not stock_info:
                return None
            
            result = {
                'id': stock_info.get('id'),
                'name': stock_info.get('name'),
                'industry': stock_info.get('industry'),
            }
            
            latest_kline = self.kline.load_latest(stock_id)
            if latest_kline:
                result.update({
                    'current_price': latest_kline.get('close'),
                    'current_price_date': latest_kline.get('date'),
                    'market_cap': latest_kline.get('total_market_value'),
                    'pe': latest_kline.get('pe'),
                    'pb': latest_kline.get('pb'),
                    'total_share': latest_kline.get('total_share'),
                    'float_share': latest_kline.get('float_share'),
                    'turnover_vol': latest_kline.get('volume'),
                    'turnover_value': latest_kline.get('amount'),
                    'turnover_rate': latest_kline.get('turnover_rate'),
                    'high': latest_kline.get('highest'),
                    'low': latest_kline.get('lowest'),
                    'open': latest_kline.get('open'),
                    'close': latest_kline.get('close'),
                })
            
            return result
