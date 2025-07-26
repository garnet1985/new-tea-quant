"""
MySQL Database Configuration
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'stocks'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'charset': 'utf8mb4',
    'autocommit': True,
    'pool_size': 10,
    'max_overflow': 20,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
}

# Table Configuration - 匹配Node.js项目的表结构
TABLES = {
    # Raw Data Tables
    'stockIndex': 'stockIndex',
    'stockKline': 'stockKline', 
    'stockDetail': 'stockDetail',
    'industryIndex': 'industryIndex',
    'industryKline': 'industryKline',
    'industryStockMap': 'industryStockMap',
    'macroEconomics': 'macroEconomics',
    'realEstate': 'realEstate',
    'corporateFinance': 'corporateFinance',
    'corporateKeyIndicator': 'corporateKeyIndicator',
    'capitalStructure': 'capitalStructure',
    
    # Strategy Tables
    'HL_OpportunityHistory': 'HL_OpportunityHistory',
    'HL_StockSummary': 'HL_StockSummary',
    'HL_Meta': 'HL_Meta',
    
    # History Tables
    'history': 'history',
    
    # Meta Tables
    'meta': 'meta',
}

# Connection Pool Settings
POOL_CONFIG = {
    'min_size': 5,
    'max_size': 20,
    'max_queries': 50000,
    'max_inactive_connection_lifetime': 300.0,
} 