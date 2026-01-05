db_config = {
  "base": {
    "name": "stocks-py",
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "stocks-py",
    "port": 3306,
    "charset": "utf8mb4"
  },
  "pool": {
    # 最小连接数
    "pool_size_min": 5,
    # 最大连接数
    "pool_size_max": 30
  },
  "performance": {
    # 最大数据包大小 16MB * 64 = 1GB
    "max_allowed_packet": 1073741824,
  },
  "timeout": {
    # 连接超时
    "connection": 60,
    # 读取超时
    "read": 60,
    # 写入超时
    "write": 60
  },
  "thread_safety": {
    # 线程安全
    "enable": True,
    # 队列大小
    "queue_size": 1000,
    # 批量处理阈值
    "turn_to_batch_threshold": 1000,
    # 最大重试次数
    "max_retries": 3
  }
}

