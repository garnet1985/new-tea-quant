# Stocks-Py - 股票分析系统

## 项目概述

这是一个基于Python的股票分析系统，从Node.js项目迁移而来，提供股票数据爬取、分析和策略模拟功能。

## 目录结构

```
stocks-py/
├── utils/                   # 通用工具模块
│   ├── __init__.py
│   └── db/                  # 数据库工具
│       ├── __init__.py
│       ├── config.py        # 数据库配置
│       ├── db_manager.py    # 数据库管理器
│       ├── models.py        # 数据模型
│       ├── README.md        # 数据库文档
│       └── tables/          # 表结构定义
│           ├── base/        # 基础表
│           └── strategy/    # 策略表
├── crawler/                 # 数据爬取模块
│   ├── providers/           # 数据提供商
│   │   └── tushare/         # Tushare API
│   │       ├── auth/        # 认证文件
│   │       ├── settings.py  # Tushare配置
│   │       └── query.py     # 数据查询
│   └── services/            # 爬虫服务
├── simulator/               # 策略模拟模块
├── start.py                 # 应用入口
├── requirements.txt         # 依赖包
└── README.md               # 本文档
```

## 核心模块

### 1. 数据库模块 (`utils/db/`)
- **功能**: 统一的MySQL数据库管理
- **特性**: 自动创建数据库和表、支持同步/异步操作
- **文档**: 详见 [utils/db/README.md](utils/db/README.md)

### 2. 数据爬取模块 (`crawler/`)
- **功能**: 从各种数据源获取股票数据
- **支持**: Tushare、东方财富等
- **配置**: 支持多数据源配置

### 3. 策略模拟模块 (`simulator/`)
- **功能**: 股票策略回测和模拟
- **特性**: 支持多种技术指标和策略

## 快速开始

### 1. 环境准备
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置数据库
```bash
# 复制环境变量模板
cp env.example .env

# 编辑数据库配置
vim .env
```

### 3. 配置Tushare
```bash
# 复制token模板
cp utils/db/tables/strategy/tushare/auth/token.example.txt utils/db/tables/strategy/tushare/auth/token.txt

# 编辑token文件，添加你的Tushare token
vim utils/db/tables/strategy/tushare/auth/token.txt
```

### 4. 启动应用
```bash
python start.py
```

## 使用示例

### 数据库操作
```python
from utils.db import DatabaseManager

# 创建数据库管理器
db = DatabaseManager()
db.connect_sync()

# 执行查询
result = db.execute_sync_query("SELECT * FROM stock_index LIMIT 5")
print(result)

db.disconnect_sync()
```

### 数据爬取
```python
from crawler.providers.tushare.query import TushareQuery

# 创建查询器
query = TushareQuery()

# 更新股票基础信息
query.renew_stock_index()
```

## 开发指南

### 添加新表
1. 在 `utils/db/tables/strategy/` 下创建新目录
2. 创建 `schema.json` 文件定义表结构
3. 在 `utils/db/config.py` 中添加表映射
4. 重启应用自动创建表

### 添加新策略
1. 在 `simulator/` 下创建策略文件
2. 实现策略逻辑
3. 在配置中注册策略

## 配置说明

### 环境变量
- `DB_HOST`: 数据库主机
- `DB_USER`: 数据库用户名
- `DB_PASSWORD`: 数据库密码
- `DB_NAME`: 数据库名称
- `DB_PORT`: 数据库端口

### Tushare配置
- Token文件: `crawler/providers/tushare/auth/token.txt`
- 配置设置: `crawler/providers/tushare/settings.py`

## 注意事项

1. **数据库安全**: 不要将数据库密码提交到版本控制
2. **API Token**: 保护好Tushare等API的token
3. **数据备份**: 定期备份重要数据
4. **测试环境**: 新功能先在测试环境验证

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证。 