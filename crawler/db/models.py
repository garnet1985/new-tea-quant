"""
Database Table Models - 匹配Node.js项目表结构
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from .db_manager import get_sync_db_manager
from .config import TABLES


class BaseModel:
    """数据库表模型基类"""
    
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.db = get_sync_db_manager()
    
    def insert(self, data: Dict[str, Any]) -> int:
        """插入数据"""
        return self.db.insert_data(self.table_name, data)
    
    def insert_many(self, data_list: List[Dict[str, Any]]) -> int:
        """批量插入数据"""
        return self.db.insert_many(self.table_name, data_list)
    
    def insert_or_update(self, data: Dict[str, Any], unique_keys: List[str]) -> int:
        """插入或更新数据"""
        return self.db.insert_or_update(self.table_name, data, unique_keys)
    
    def update(self, data: Dict[str, Any], condition: str, params: tuple) -> int:
        """更新数据"""
        return self.db.update_data(self.table_name, data, condition, params)
    
    def delete(self, condition: str, params: tuple) -> int:
        """删除数据"""
        return self.db.delete_data(self.table_name, condition, params)
    
    def find_one(self, condition: str = "1=1", params: tuple = ()) -> Optional[Dict[str, Any]]:
        """查找单条记录"""
        query = f"SELECT * FROM {self.table_name} WHERE {condition} LIMIT 1"
        result = self.db.execute_query(query, params)
        return result[0] if result else None
    
    def find_many(self, condition: str = "1=1", params: tuple = (), limit: int = None, order_by: str = None) -> List[Dict[str, Any]]:
        """查找多条记录"""
        query = f"SELECT * FROM {self.table_name} WHERE {condition}"
        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit}"
        return self.db.execute_query(query, params)
    
    def count(self, condition: str = "1=1", params: tuple = ()) -> int:
        """统计记录数"""
        return self.db.get_table_count(self.table_name, condition, params)


class StockIndexModel(BaseModel):
    """股票指数表模型"""
    
    def __init__(self):
        super().__init__(TABLES['stockIndex'])
    
    def get_stock_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """根据代码获取股票信息"""
        return self.find_one("code = %s", (code,))
    
    def get_stocks_by_market(self, market: int) -> List[Dict[str, Any]]:
        """根据市场获取股票列表"""
        return self.find_many("market = %s", (market,))
    
    def get_all_stocks(self) -> List[Dict[str, Any]]:
        """获取所有股票"""
        return self.find_many()
    
    def update_last_update(self, code: str, last_update: str) -> int:
        """更新最后更新时间"""
        return self.update(
            {"lastUpdate": last_update},
            "code = %s",
            (code,)
        )


class StockKlineModel(BaseModel):
    """股票K线数据表模型"""
    
    def __init__(self):
        super().__init__(TABLES['stockKline'])
    
    def get_stock_kline_data(self, code: str, term: str = None, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """获取股票K线数据"""
        condition = "code = %s"
        params = [code]
        
        if term:
            condition += " AND term = %s"
            params.append(term)
        
        if start_date:
            condition += " AND date >= %s"
            params.append(start_date)
        
        if end_date:
            condition += " AND date <= %s"
            params.append(end_date)
        
        return self.find_many(condition, tuple(params), order_by="dateTime DESC")
    
    def get_latest_kline(self, code: str, term: str = "daily") -> Optional[Dict[str, Any]]:
        """获取最新K线数据"""
        return self.find_one("code = %s AND term = %s", (code, term), order_by="dateTime DESC")
    
    def get_data_by_date(self, date: str, term: str = "daily") -> List[Dict[str, Any]]:
        """根据日期获取所有股票K线数据"""
        return self.find_many("date = %s AND term = %s", (date, term))
    
    def get_price_range(self, code: str, term: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """获取价格区间统计"""
        query = """
        SELECT 
            MIN(lowest) as min_price,
            MAX(highest) as max_price,
            AVG(close) as avg_price,
            COUNT(*) as days_count
        FROM stockKline 
        WHERE code = %s AND term = %s AND date BETWEEN %s AND %s
        """
        result = self.db.execute_query(query, (code, term, start_date, end_date))
        return result[0] if result else {}


class StockDetailModel(BaseModel):
    """股票详情表模型"""
    
    def __init__(self):
        super().__init__(TABLES['stockDetail'])
    
    def get_stock_detail(self, code: str, date: str = None) -> Optional[Dict[str, Any]]:
        """获取股票详情"""
        if date:
            return self.find_one("code = %s AND date = %s", (code, date))
        else:
            return self.find_one("code = %s", (code,), order_by="date DESC")
    
    def get_stocks_by_market(self, market: int, date: str = None) -> List[Dict[str, Any]]:
        """根据市场获取股票详情列表"""
        if date:
            return self.find_many("market = %s AND date = %s", (market, date))
        else:
            return self.find_many("market = %s", (market,), order_by="date DESC")


class IndustryIndexModel(BaseModel):
    """行业指数表模型"""
    
    def __init__(self):
        super().__init__(TABLES['industryIndex'])
    
    def get_industry_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """根据代码获取行业信息"""
        return self.find_one("code = %s", (code,))
    
    def get_all_industries(self) -> List[Dict[str, Any]]:
        """获取所有行业"""
        return self.find_many()


class IndustryKlineModel(BaseModel):
    """行业K线数据表模型"""
    
    def __init__(self):
        super().__init__(TABLES['industryKline'])
    
    def get_industry_kline_data(self, code: str, term: str = None, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """获取行业K线数据"""
        condition = "code = %s"
        params = [code]
        
        if term:
            condition += " AND term = %s"
            params.append(term)
        
        if start_date:
            condition += " AND date >= %s"
            params.append(start_date)
        
        if end_date:
            condition += " AND date <= %s"
            params.append(end_date)
        
        return self.find_many(condition, tuple(params), order_by="dateTime DESC")


class IndustryStockMapModel(BaseModel):
    """行业股票映射表模型"""
    
    def __init__(self):
        super().__init__(TABLES['industryStockMap'])
    
    def get_stocks_by_industry(self, industry_code: str) -> List[Dict[str, Any]]:
        """根据行业代码获取股票列表"""
        return self.find_many("industryCode = %s", (industry_code,))
    
    def get_industry_by_stock(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """根据股票代码获取行业信息"""
        return self.find_one("stockCode = %s", (stock_code,))
    
    def get_all_mappings(self) -> List[Dict[str, Any]]:
        """获取所有映射关系"""
        return self.find_many()


class MacroEconomicsModel(BaseModel):
    """宏观经济数据表模型"""
    
    def __init__(self):
        super().__init__(TABLES['macroEconomics'])
    
    def get_data_by_name(self, name: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """根据指标名称获取数据"""
        condition = "name = %s"
        params = [name]
        
        if start_date:
            condition += " AND reportDate >= %s"
            params.append(start_date)
        
        if end_date:
            condition += " AND reportDate <= %s"
            params.append(end_date)
        
        return self.find_many(condition, tuple(params), order_by="dateTime DESC")
    
    def get_latest_data(self, name: str) -> Optional[Dict[str, Any]]:
        """获取最新数据"""
        return self.find_one("name = %s", (name,), order_by="dateTime DESC")


class RealEstateModel(BaseModel):
    """房地产数据表模型"""
    
    def __init__(self):
        super().__init__(TABLES['realEstate'])
    
    def get_data_by_name(self, name: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """根据指标名称获取数据"""
        condition = "name = %s"
        params = [name]
        
        if start_date:
            condition += " AND reportDate >= %s"
            params.append(start_date)
        
        if end_date:
            condition += " AND reportDate <= %s"
            params.append(end_date)
        
        return self.find_many(condition, tuple(params), order_by="dateTime DESC")


class HLOpportunityHistoryModel(BaseModel):
    """历史低点策略机会历史表模型"""
    
    def __init__(self):
        super().__init__(TABLES['HL_OpportunityHistory'])
    
    def get_opportunities_by_code(self, code: str) -> List[Dict[str, Any]]:
        """根据股票代码获取机会历史"""
        return self.find_many("code = %s", (code,), order_by="startDate DESC")
    
    def get_opportunities_by_status(self, status: str) -> List[Dict[str, Any]]:
        """根据状态获取机会"""
        return self.find_many("status = %s", (status,), order_by="startDate DESC")
    
    def get_active_opportunities(self) -> List[Dict[str, Any]]:
        """获取活跃的机会"""
        return self.find_many("status = 'active'", order_by="startDate DESC")
    
    def get_completed_opportunities(self) -> List[Dict[str, Any]]:
        """获取已完成的机会"""
        return self.find_many("status = 'completed'", order_by="endDate DESC")


class HLStockSummaryModel(BaseModel):
    """历史低点策略股票汇总表模型"""
    
    def __init__(self):
        super().__init__(TABLES['HL_StockSummary'])
    
    def get_summary_by_code(self, code: str) -> Optional[Dict[str, Any]]:
        """根据股票代码获取汇总信息"""
        return self.find_one("code = %s", (code,))
    
    def get_all_summaries(self) -> List[Dict[str, Any]]:
        """获取所有汇总信息"""
        return self.find_many()


class HLMetaModel(BaseModel):
    """历史低点策略元数据表模型"""
    
    def __init__(self):
        super().__init__(TABLES['HL_Meta'])
    
    def get_meta_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """根据键获取元数据"""
        return self.find_one("meta_key = %s", (key,))
    
    def update_meta(self, key: str, value: str) -> int:
        """更新元数据"""
        return self.insert_or_update(
            {"meta_key": key, "meta_value": value, "updated_at": datetime.now()},
            ["meta_key"]
        )


# 模型实例
stock_index_model = StockIndexModel()
stock_kline_model = StockKlineModel()
stock_detail_model = StockDetailModel()
industry_index_model = IndustryIndexModel()
industry_kline_model = IndustryKlineModel()
industry_stock_map_model = IndustryStockMapModel()
macro_economics_model = MacroEconomicsModel()
real_estate_model = RealEstateModel()
hl_opportunity_history_model = HLOpportunityHistoryModel()
hl_stock_summary_model = HLStockSummaryModel()
hl_meta_model = HLMetaModel() 