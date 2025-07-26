"""
Database Package - 匹配Node.js项目表结构
"""
from .config import DB_CONFIG, TABLES, POOL_CONFIG
from .connection import DatabaseConnection, get_db_connection
from .sync_connection import SyncDatabaseConnection, get_sync_db_connection
from .models import (
    BaseModel,
    StockIndexModel,
    StockKlineModel,
    StockDetailModel,
    IndustryIndexModel,
    IndustryKlineModel,
    IndustryStockMapModel,
    MacroEconomicsModel,
    RealEstateModel,
    HLOpportunityHistoryModel,
    HLStockSummaryModel,
    HLMetaModel,
    # 模型实例
    stock_index_model,
    stock_kline_model,
    stock_detail_model,
    industry_index_model,
    industry_kline_model,
    industry_stock_map_model,
    macro_economics_model,
    real_estate_model,
    hl_opportunity_history_model,
    hl_stock_summary_model,
    hl_meta_model,
)
from .init_db import check_database_connection, show_table_info, test_model_operations, get_database_summary

__all__ = [
    # Config
    'DB_CONFIG',
    'TABLES', 
    'POOL_CONFIG',
    
    # Connection classes
    'DatabaseConnection',
    'SyncDatabaseConnection',
    
    # Connection functions
    'get_db_connection',
    'get_sync_db_connection',
    
    # Models
    'BaseModel',
    'StockIndexModel',
    'StockKlineModel',
    'StockDetailModel',
    'IndustryIndexModel',
    'IndustryKlineModel',
    'IndustryStockMapModel',
    'MacroEconomicsModel',
    'RealEstateModel',
    'HLOpportunityHistoryModel',
    'HLStockSummaryModel',
    'HLMetaModel',
    
    # Model instances
    'stock_index_model',
    'stock_kline_model',
    'stock_detail_model',
    'industry_index_model',
    'industry_kline_model',
    'industry_stock_map_model',
    'macro_economics_model',
    'real_estate_model',
    'hl_opportunity_history_model',
    'hl_stock_summary_model',
    'hl_meta_model',
    
    # Database utilities
    'check_database_connection',
    'show_table_info',
    'test_model_operations',
    'get_database_summary',
] 