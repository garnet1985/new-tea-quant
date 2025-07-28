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
    }
}