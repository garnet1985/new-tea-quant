"""
Configuration settings for the stocks analysis project
"""

# Date range for data collection
START_DATE = '20200101'
END_DATE = '20241231'

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': 'root',
    'database': 'stocks',
    'charset': 'utf8mb4'
}

# Tushare configuration
TUSHARE_TOKEN = 'your_tushare_token_here'

# API configuration
API_BASE_URL = 'http://117.72.14.170:8010'
API_TOKEN_ENDPOINT = '/stock/s475652a0cb1b38f73d16c000d385ddf7c582ed5' 