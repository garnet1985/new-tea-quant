"""
Database Package - 匹配Node.js项目表结构
"""
from .config import DB_CONFIG, TABLES, STRATEGY_TABLES, TABLE_SCHEMA_PATH
from .db_manager import DatabaseManager, get_db_manager, get_sync_db_manager
# from .models import (
#     BaseModel,
#     StockIndexModel,
#     StockKlineModel,
#     StockDetailModel,
#     IndustryIndexModel,
#     IndustryKlineModel,
#     IndustryStockMapModel,
#     MacroEconomicsModel,
#     RealEstateModel,
#     HLOpportunityHistoryModel,
#     HLStockSummaryModel,
#     HLMetaModel,
#     # 模型实例
#     stock_index_model,
#     stock_kline_model,
#     stock_detail_model,
#     industry_index_model,
#     industry_kline_model,
#     industry_stock_map_model,
#     macro_economics_model,
#     real_estate_model,
#     hl_opportunity_history_model,
#     hl_stock_summary_model,
#     hl_meta_model,
# )


__all__ = [
    # Config
    'DB_CONFIG',
    'TABLES',
    'STRATEGY_TABLES',
    'TABLE_SCHEMA_PATH',
    
    # Database Manager
    'DatabaseManager',
    'get_db_manager',
    'get_sync_db_manager',
    
    # Models (暂时注释)
    # 'BaseModel',
    # 'StockIndexModel',
    # 'StockKlineModel',
    # 'StockDetailModel',
    # 'IndustryIndexModel',
    # 'IndustryKlineModel',
    # 'IndustryStockMapModel',
    # 'MacroEconomicsModel',
    # 'RealEstateModel',
    # 'HLOpportunityHistoryModel',
    # 'HLStockSummaryModel',
    # 'HLMetaModel',
    
    # Model instances (暂时注释)
    # 'stock_index_model',
    # 'stock_kline_model',
    # 'stock_detail_model',
    # 'industry_index_model',
    # 'industry_kline_model',
    # 'industry_stock_map_model',
    # 'macro_economics_model',
    # 'real_estate_model',
    # 'hl_opportunity_history_model',
    # 'hl_stock_summary_model',
    # 'hl_meta_model',
    

] 