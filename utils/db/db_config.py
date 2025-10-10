"""
MySQL Database Configuration
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database Configuration
DB_CONFIG = {
    'base': {
        'name': 'stocks-py',
        'host': os.getenv('DB_HOST', 'localhost'),
        'user': os.getenv('DB_USER', 'root'),
        'password': os.getenv('DB_PASSWORD', ''),
        'database': os.getenv('DB_NAME', 'stocks-py'),
        'port': int(os.getenv('DB_PORT', 3306)),
        'charset': 'utf8mb4',
        'autocommit': True,
    },
    'pool': {
        'pool_size_min': 5,
        'pool_size_max': 30
    },
    'performance': {
        'max_allowed_packet': 16777216 * 64,  # 16MB * 32 = 512MB
    },
    'timeout': {
        'connection': 60,
        'read': 60,
        'write': 60,
    },

    'thread_safety': {
        'enable': True,
        'queue_size': 1000,
        'turn_to_batch_threshold': 1000,
        'max_retries': 3,
    },

    # 股票列表相关配置 - 在数据库中获取股票列表时，排除这些代码 688开头的科创板已经北交所的股票
    # 注意：这些股票仍然会在获取数据时存入数据库，只是在读取数据库时排除在外
    'stock_list': {
        'ts_code_exclude_list': ('688%', '%BJ%')
    }
}