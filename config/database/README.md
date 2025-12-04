# 数据库配置

## 文件说明

- `db_config.json`: 实际的数据库配置文件（**不提交到 Git**）
- `db_config.example.json`: 配置文件模板（提交到 Git）

## 使用方法

1. 复制示例文件：
```bash
cp db_config.example.json db_config.json
```

2. 修改 `db_config.json` 中的配置：
```json
{
  "base": {
    "host": "your_host",
    "user": "your_user",
    "password": "your_password",
    "database": "your_database",
    "port": 3306,
    "charset": "utf8mb4",
    "autocommit": true
  },
  "pool": {
    "pool_size_min": 5,
    "pool_size_max": 30
  }
}
```

3. 配置会被 `utils/db/db_config.py` 自动导入

## 配置说明

### base（数据库连接）
- `host`: 数据库主机地址
- `user`: 数据库用户名
- `password`: 数据库密码
- `database`: 数据库名称
- `port`: 数据库端口（默认 3306）
- `charset`: 字符集（推荐 utf8mb4）
- `autocommit`: 是否自动提交（推荐 true）

### pool（连接池）
- `pool_size_min`: 最小连接数
- `pool_size_max`: 最大连接数

### performance（性能）
- `max_allowed_packet`: 最大数据包大小（字节）

### timeout（超时）
- `connection`: 连接超时（秒）
- `read`: 读取超时（秒）
- `write`: 写入超时（秒）

### thread_safety（线程安全）
- `enable`: 是否启用线程安全
- `queue_size`: 队列大小
- `turn_to_batch_threshold`: 批量处理阈值
- `max_retries`: 最大重试次数

### stock_list（股票列表）
- `ts_code_exclude_list`: 排除的股票代码模式（支持通配符）

## 注意事项

- ⚠️ `db_config.json` 已添加到 `.gitignore`，不会被提交
- ✅ JSON 格式更通用，Python 原生支持
- 📝 如需添加新配置项，请同时更新 `db_config.example.json`
- 💡 可以使用 `_comment` 字段添加注释（会被程序忽略）
