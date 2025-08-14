# Stocks-Py - 股票分析系统

## 项目概述

Stocks-Py 是一个基于Python的股票分析系统，从Node.js项目迁移而来，提供股票数据爬取、分析、策略回测和模拟交易功能。系统采用模块化设计，支持多种数据源和自定义策略。

## 核心特性

- 🚀 **多数据源支持**: 集成Tushare、AKShare等主流数据源
- 📊 **智能分析**: 内置多种技术指标和趋势分析算法
- 🎯 **策略回测**: 完整的策略回测和模拟交易系统
- 🗄️ **数据管理**: 自动化的数据库管理和表结构维护
- 🔧 **可扩展性**: 支持自定义策略和指标
- 📈 **实时监控**: 股票机会监控和预警系统

## 系统架构

```
stocks-py/
├── app/                     # 核心应用模块
│   ├── analyzer/           # 分析器模块
│   │   ├── strategy/       # 策略实现
│   │   │   ├── historicLow/    # 历史低点策略
│   │   │   └── lowPrice/       # 低价策略
│   │   └── libs/           # 分析库
│   ├── data_source/        # 数据源管理
│   │   └── providers/      # 数据提供商
│   │       ├── tushare/    # Tushare API
│   │       └── akshare/    # AKShare API
│   └── simulator/          # 策略模拟器 （还未完成...）
├── utils/                   # 通用工具模块
│   ├── db/                 # 数据库管理
│   └── worker/             # 异步任务处理
├── config/                  # 配置文件
├── tools/                   # 辅助工具
└── start.py                # 应用入口
```

## 快速开始

### 1. 环境要求

- Python 3.8+
- MySQL 5.7+
- 8GB+ RAM (推荐)

### 2. 安装步骤

```bash
# 克隆项目
git clone <repository-url>
cd stocks-py

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置数据库

```bash
# 复制配置文件模板
cp config/app_config.example.json config/app_config.json

# 编辑数据库配置
vim config/app_config.json
```

配置示例：
```json
{
    "database": {
        "host": "localhost",
        "user": "root",
        "password": "your_password",
        "database": "stocks_py",
        "port": 3306
    }
}
```

### 4. 配置数据源

#### Tushare配置
```bash
# 复制token模板
cp app/data_source/providers/tushare/auth/token.example.txt \
   app/data_source/providers/tushare/auth/token.txt

# 编辑token文件
vim app/data_source/providers/tushare/auth/token.txt
```

#### AKShare配置
```bash
# 编辑AKShare配置
vim app/data_source/providers/akshare/main_settings.py
```

### 5. 启动应用

```bash
# 启动主应用
python start.py

# 或启动特定模块
python -m app.analyzer.analyzer
```

## 核心模块详解

### 1. 分析器模块 (`app/analyzer/`)

分析器是系统的核心，负责股票数据分析和策略执行。

**主要功能:**
- 技术指标计算
- 趋势分析
- 策略信号生成
- 机会识别

**使用方法:**
```python
from app.analyzer import Analyzer

analyzer = Analyzer()
# 分析股票
result = analyzer.analyze_stock('000001.SZ')
```

**添加自定义策略:**
详见 [app/analyzer/README.md](app/analyzer/README.md)

### 2. 数据源模块 (`app/data_source/`)

统一管理多个数据源，提供一致的数据接口。

**支持的数据源:**
- **Tushare**: 专业金融数据API
- **AKShare**: 开源金融数据接口
- **自定义数据源**: 支持扩展

**使用方法:**
```python
from app.data_source import DataSourceManager

dsm = DataSourceManager()
# 获取股票数据
data = dsm.get_stock_data('000001.SZ', 'daily')
```

### 3. 策略模块 (`app/analyzer/strategy/`)

实现各种交易策略，支持回测和模拟。

**内置策略:**
- **HistoricLow**: 历史低点策略
- **LowPrice**: 低价策略

**策略结构:**
```
strategy/
├── strategy.py          # 策略逻辑
├── strategy_service.py  # 策略服务
├── strategy_settings.py # 策略配置
└── tables/             # 策略数据表
```

**自定义策略:**
详见 [app/analyzer/strategy/README.md](app/analyzer/strategy/README.md)

### 4. 数据库模块 (`utils/db/`)

自动化的数据库管理，支持表结构自动创建和维护。

**特性:**
- 自动创建数据库和表
- 支持同步/异步操作
- 表结构版本管理
- 数据迁移支持

**使用方法:**
```python
from utils.db import DatabaseManager

db = DatabaseManager()
db.connect_sync()
db.create_tables()  # 自动创建所有表
```

**表管理:**
详见 [utils/db/README.md](utils/db/README.md)

## 使用示例

### 基础数据分析

```python
from app.analyzer import Analyzer
from app.data_source import DataSourceManager

# 初始化
analyzer = Analyzer()
dsm = DataSourceManager()

# 获取股票数据
stock_data = dsm.get_stock_data('000001.SZ', 'daily')

# 分析数据
analysis = analyzer.analyze_stock_data(stock_data)
print(analysis)
```

### 策略回测

```python
from app.analyzer.strategy.historicLow.strategy_simulator import StrategySimulator

# 创建模拟器
simulator = StrategySimulator()

# 运行回测
results = simulator.run_backtest(
    start_date='2023-01-01',
    end_date='2023-12-31',
    symbols=['000001.SZ', '000002.SZ']
)

# 查看结果
print(results.summary())
```

### 实时监控

```python
from app.analyzer.analyzer_service import AnalyzerService

# 启动监控服务
service = AnalyzerService()
service.start_monitoring()

# 监控特定股票
service.monitor_stock('000001.SZ')
```

## 配置说明

### 应用配置 (`config/app_config.json`)

```json
{
    "database": {
        "host": "localhost",
        "user": "root",
        "password": "password",
        "database": "stocks_py",
        "port": 3306
    },
    "data_sources": {
        "tushare": {
            "enabled": true,
            "token": "your_token_file_path"
        },
        "akshare": {
            "enabled": true
        }
    },
    "analyzer": {
        "update_interval": 300,
        "max_workers": 4
    }
}
```

### 策略配置

每个策略都有自己的配置文件，位于 `strategy/strategy_name/strategy_settings.py`。

## 开发指南

### 添加新策略

1. 在 `app/analyzer/strategy/` 下创建新目录
2. 实现策略逻辑 (`strategy.py`)
3. 创建策略服务 (`strategy_service.py`)
4. 配置策略参数 (`strategy_settings.py`)
5. 添加数据表定义

### 添加新数据源

1. 在 `app/data_source/providers/` 下创建新目录
2. 实现数据接口
3. 在 `data_source_manager.py` 中注册
4. 更新配置

### 添加新指标

1. 在 `app/analyzer/libs/` 下创建指标文件
2. 实现计算逻辑
3. 在分析器中集成

## 部署说明

### 生产环境部署

```bash
# 使用Gunicorn部署
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 start:app

# 使用Docker部署
docker build -t stocks-py .
docker run -d -p 8000:8000 stocks-py
```

### 系统服务

```bash
# 创建系统服务
sudo cp stocks-py.service /etc/systemd/system/
sudo systemctl enable stocks-py
sudo systemctl start stocks-py
```

## 监控和维护

### 日志管理

```bash
# 查看应用日志
tail -f logs/app.log

# 查看错误日志
tail -f logs/error.log
```

### 性能监控

```bash
# 监控数据库性能
python tools/monitor_db.py

# 监控策略性能
python tools/monitor_strategy.py
```

### 数据备份

```bash
# 备份数据库
mysqldump -u root -p stocks_py > backup_$(date +%Y%m%d).sql

# 备份配置文件
tar -czf config_backup_$(date +%Y%m%d).tar.gz config/
```

## 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库服务状态
   - 验证连接参数
   - 确认网络连接

2. **数据源API错误**
   - 检查API token有效性
   - 确认API调用限制
   - 查看错误日志

3. **策略执行异常**
   - 检查策略配置
   - 验证数据完整性
   - 查看策略日志

### 调试模式

```python
# 启用调试模式
import logging
logging.basicConfig(level=logging.DEBUG)

# 或修改配置文件
{
    "debug": true,
    "log_level": "DEBUG"
}
```

## 性能优化

### 数据库优化

- 合理设计索引
- 使用连接池
- 定期清理历史数据

### 策略优化

- 使用缓存减少重复计算
- 批量处理数据
- 异步执行非关键任务

### 系统优化

- 调整工作进程数
- 使用Redis缓存
- 优化内存使用

## 贡献指南

### 开发流程

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 代码规范

- 遵循PEP 8编码规范
- 添加适当的注释和文档
- 编写单元测试
- 确保代码通过所有测试

### 提交规范

```
feat: 添加新功能
fix: 修复bug
docs: 更新文档
style: 代码格式调整
refactor: 代码重构
test: 添加测试
chore: 构建过程或辅助工具的变动
```

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目主页: [GitHub Repository]
- 问题反馈: [Issues]
- 功能建议: [Discussions]

## 更新日志

### v2.0.0 (2024-01-XX)
- 从Node.js迁移到Python
- 重构系统架构
- 添加多数据源支持
- 优化策略回测系统

### v1.0.0 (2023-XX-XX)
- 初始版本发布
- 基础股票分析功能
- 简单策略回测

---

**注意**: 本项目仅供学习和研究使用，不构成投资建议。投资有风险，入市需谨慎。
