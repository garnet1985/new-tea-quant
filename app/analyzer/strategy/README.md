# Strategy Tables - 策略表自定义指南

## 概述

策略表用于存储策略执行过程中产生的数据，如信号、回测结果、策略配置等。本指南将详细介绍如何创建和自定义策略表。

## 目录结构

```
strategy/
├── historicLow/            # 历史低点策略
│   ├── tables/            # 策略数据表
│   │   ├── meta/          # 策略元数据表
│   │   ├── opportunity_history/  # 机会历史表
│   │   └── strategy_summary/     # 策略汇总表
│   ├── strategy.py        # 策略逻辑
│   ├── strategy_service.py # 策略服务
│   └── strategy_settings.py # 策略配置
├── lowPrice/              # 低价策略
│   └── tables/            # 策略数据表
└── README.md              # 本文档
```

## 策略表设计原则

### 1. 命名规范

- **表名**: 使用小写字母和下划线，如 `opportunity_history`
- **字段名**: 使用小写字母和下划线，如 `created_at`
- **索引名**: 使用 `idx_` 前缀，如 `idx_ts_code_date`

### 2. 字段设计

- **必需字段**: 每个表都应该包含 `id`、`created_at`、`updated_at`
- **业务字段**: 根据策略需求设计具体业务字段
- **状态字段**: 使用状态字段标识记录状态，如 `status`、`is_active`

### 3. 索引设计

- **主键索引**: 每个表必须有主键
- **业务索引**: 为经常查询的字段创建索引
- **复合索引**: 为多字段查询创建复合索引

## 创建自定义策略表

### 步骤1: 创建策略目录结构

```bash
# 在 strategy 目录下创建新策略
mkdir -p app/analyzer/strategy/myStrategy/tables
cd app/analyzer/strategy/myStrategy

# 创建必要的文件
touch strategy.py
touch strategy_service.py
touch strategy_settings.py
touch tables/__init__.py
```

### 步骤2: 设计表结构

在 `tables/` 目录下创建表定义文件。以 `opportunity_history` 表为例：

```python
# tables/opportunity_history/model.py
from utils.db.db_model import TableModel

class OpportunityHistory(TableModel):
    """机会历史表模型"""
    
    def __init__(self):
        super().__init__()
        self.table_name = "opportunity_history"
    
    def get_schema(self):
        """获取表结构定义"""
        return {
            "name": "opportunity_history",
            "primaryKey": "id",
            "fields": [
                {
                    "name": "id",
                    "type": "int",
                    "isRequired": True,
                    "autoIncrement": True
                },
                {
                    "name": "ts_code",
                    "type": "varchar",
                    "length": 10,
                    "isRequired": True,
                    "comment": "股票代码"
                },
                {
                    "name": "signal_type",
                    "type": "varchar",
                    "length": 20,
                    "isRequired": True,
                    "comment": "信号类型：BUY/SELL/HOLD"
                },
                {
                    "name": "signal_strength",
                    "type": "decimal",
                    "length": "5,2",
                    "isRequired": True,
                    "comment": "信号强度：0.00-1.00"
                },
                {
                    "name": "price",
                    "type": "decimal",
                    "length": "10,2",
                    "isRequired": True,
                    "comment": "信号触发时的价格"
                },
                {
                    "name": "volume",
                    "type": "decimal",
                    "length": "20,2",
                    "isRequired": False,
                    "comment": "成交量"
                },
                {
                    "name": "reason",
                    "type": "text",
                    "isRequired": False,
                    "comment": "信号触发原因"
                },
                {
                    "name": "status",
                    "type": "varchar",
                    "length": 20,
                    "isRequired": True,
                    "default": "PENDING",
                    "comment": "状态：PENDING/EXECUTED/CANCELLED"
                },
                {
                    "name": "created_at",
                    "type": "datetime",
                    "isRequired": True,
                    "comment": "创建时间"
                },
                {
                    "name": "updated_at",
                    "type": "datetime",
                    "isRequired": True,
                    "comment": "更新时间"
                }
            ],
            "indexes": [
                {
                    "name": "idx_ts_code",
                    "columns": ["ts_code"],
                    "type": "BTREE"
                },
                {
                    "name": "idx_signal_type",
                    "columns": ["signal_type"],
                    "type": "BTREE"
                },
                {
                    "name": "idx_created_at",
                    "columns": ["created_at"],
                    "type": "BTREE"
                },
                {
                    "name": "idx_ts_code_date",
                    "columns": ["ts_code", "created_at"],
                    "type": "BTREE"
                }
            ]
        }
```

### 步骤3: 创建表操作类

```python
# tables/opportunity_history/opportunity_history_service.py
from datetime import datetime
from utils.db import DatabaseManager
from .model import OpportunityHistory

class OpportunityHistoryService:
    """机会历史服务类"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.model = OpportunityHistory()
    
    def create_opportunity(self, ts_code, signal_type, signal_strength, 
                          price, volume=None, reason=None):
        """创建新的机会记录"""
        try:
            self.db.connect_sync()
            
            query = """
            INSERT INTO opportunity_history 
            (ts_code, signal_type, signal_strength, price, volume, reason, 
             status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            now = datetime.now()
            values = (ts_code, signal_type, signal_strength, price, 
                     volume, reason, 'PENDING', now, now)
            
            result = self.db.execute_sync_query(query, values)
            return result
            
        except Exception as e:
            print(f"创建机会记录失败: {e}")
            raise
        finally:
            self.db.disconnect_sync()
    
    def get_opportunities_by_stock(self, ts_code, limit=100):
        """获取某股票的机会历史"""
        try:
            self.db.connect_sync()
            
            query = """
            SELECT * FROM opportunity_history 
            WHERE ts_code = %s 
            ORDER BY created_at DESC 
            LIMIT %s
            """
            
            result = self.db.execute_sync_query(query, (ts_code, limit))
            return result
            
        except Exception as e:
            print(f"查询机会历史失败: {e}")
            raise
        finally:
            self.db.disconnect_sync()
    
    def update_opportunity_status(self, opportunity_id, new_status):
        """更新机会状态"""
        try:
            self.db.connect_sync()
            
            query = """
            UPDATE opportunity_history 
            SET status = %s, updated_at = %s 
            WHERE id = %s
            """
            
            now = datetime.now()
            result = self.db.execute_sync_query(query, (new_status, now, opportunity_id))
            return result
            
        except Exception as e:
            print(f"更新机会状态失败: {e}")
            raise
        finally:
            self.db.disconnect_sync()
    
    def get_pending_opportunities(self):
        """获取所有待处理的机会"""
        try:
            self.db.connect_sync()
            
            query = """
            SELECT * FROM opportunity_history 
            WHERE status = 'PENDING' 
            ORDER BY created_at ASC
            """
            
            result = self.db.execute_sync_query(query)
            return result
            
        except Exception as e:
            print(f"查询待处理机会失败: {e}")
            raise
        finally:
            self.db.disconnect_sync()
```

### 步骤4: 在策略中使用表

```python
# strategy.py
from .tables.opportunity_history.opportunity_history_service import OpportunityHistoryService

class MyStrategy:
    """我的自定义策略"""
    
    def __init__(self):
        self.opportunity_service = OpportunityHistoryService()
    
    def analyze_stock(self, ts_code, stock_data):
        """分析股票并生成信号"""
        # 策略分析逻辑
        signal_type = self._generate_signal(stock_data)
        signal_strength = self._calculate_strength(stock_data)
        current_price = stock_data['close']
        
        if signal_type in ['BUY', 'SELL']:
            # 创建机会记录
            self.opportunity_service.create_opportunity(
                ts_code=ts_code,
                signal_type=signal_type,
                signal_strength=signal_strength,
                price=current_price,
                reason="技术指标触发信号"
            )
    
    def _generate_signal(self, stock_data):
        """生成交易信号"""
        # 实现你的信号生成逻辑
        pass
    
    def _calculate_strength(self, stock_data):
        """计算信号强度"""
        # 实现你的强度计算逻辑
        pass
```

## 高级表设计模式

### 1. 分表策略

对于数据量大的表，可以使用分表策略：

```python
# 按月分表的K线数据表
class MonthlyKlineTable:
    """月度K线分表"""
    
    def __init__(self, year, month):
        self.table_name = f"stock_kline_{year}_{month:02d}"
    
    def get_schema(self):
        return {
            "name": self.table_name,
            "primaryKey": "id",
            "fields": [
                # ... 字段定义
            ]
        }
    
    def create_monthly_table(self, year, month):
        """创建月度表"""
        # 实现分表创建逻辑
        pass
```

### 2. 缓存表设计

```python
# 缓存表用于存储计算结果
class StrategyCacheTable:
    """策略缓存表"""
    
    def get_schema(self):
        return {
            "name": "strategy_cache",
            "primaryKey": "id",
            "fields": [
                {
                    "name": "cache_key",
                    "type": "varchar",
                    "length": 100,
                    "isRequired": True,
                    "comment": "缓存键"
                },
                {
                    "name": "cache_value",
                    "type": "json",
                    "isRequired": True,
                    "comment": "缓存值"
                },
                {
                    "name": "expires_at",
                    "type": "datetime",
                    "isRequired": True,
                    "comment": "过期时间"
                }
            ],
            "indexes": [
                {
                    "name": "idx_cache_key",
                    "columns": ["cache_key"],
                    "type": "BTREE"
                },
                {
                    "name": "idx_expires_at",
                    "columns": ["expires_at"],
                    "type": "BTREE"
                }
            ]
        }
```

### 3. 日志表设计

```python
# 策略执行日志表
class StrategyLogTable:
    """策略执行日志表"""
    
    def get_schema(self):
        return {
            "name": "strategy_log",
            "primaryKey": "id",
            "fields": [
                {
                    "name": "strategy_name",
                    "type": "varchar",
                    "length": 50,
                    "isRequired": True,
                    "comment": "策略名称"
                },
                {
                    "name": "log_level",
                    "type": "varchar",
                    "length": 10,
                    "isRequired": True,
                    "comment": "日志级别：INFO/WARN/ERROR"
                },
                {
                    "name": "message",
                    "type": "text",
                    "isRequired": True,
                    "comment": "日志消息"
                },
                {
                    "name": "context",
                    "type": "json",
                    "isRequired": False,
                    "comment": "上下文信息"
                }
            ],
            "indexes": [
                {
                    "name": "idx_strategy_date",
                    "columns": ["strategy_name", "created_at"],
                    "type": "BTREE"
                }
            ]
        }
```

## 数据迁移和版本管理

### 1. 表结构版本控制

```python
# 版本管理类
class TableVersionManager:
    """表版本管理器"""
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def get_current_version(self, table_name):
        """获取表当前版本"""
        query = "SELECT version FROM table_versions WHERE table_name = %s"
        result = self.db.execute_sync_query(query, (table_name,))
        return result[0]['version'] if result else 1
    
    def update_version(self, table_name, new_version):
        """更新表版本"""
        query = """
        INSERT INTO table_versions (table_name, version, updated_at) 
        VALUES (%s, %s, NOW()) 
        ON DUPLICATE KEY UPDATE version = %s, updated_at = NOW()
        """
        self.db.execute_sync_query(query, (table_name, new_version, new_version))
    
    def migrate_table(self, table_name, from_version, to_version):
        """执行表迁移"""
        # 实现迁移逻辑
        pass
```

### 2. 数据备份和恢复

```python
class TableBackupManager:
    """表备份管理器"""
    
    def backup_table(self, table_name, backup_file):
        """备份表数据"""
        query = f"SELECT * FROM {table_name}"
        result = self.db.execute_sync_query(query)
        
        # 导出到文件
        import json
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    
    def restore_table(self, table_name, backup_file):
        """恢复表数据"""
        import json
        with open(backup_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 清空表
        self.db.execute_sync_query(f"TRUNCATE TABLE {table_name}")
        
        # 恢复数据
        for row in data:
            # 构建插入语句
            fields = list(row.keys())
            placeholders = ', '.join(['%s'] * len(fields))
            query = f"INSERT INTO {table_name} ({', '.join(fields)}) VALUES ({placeholders})"
            self.db.execute_sync_query(query, list(row.values()))
```

## 性能优化

### 1. 索引优化

```python
# 创建复合索引优化查询
def create_optimized_indexes(self):
    """创建优化索引"""
    indexes = [
        "CREATE INDEX idx_ts_code_signal_date ON opportunity_history(ts_code, signal_type, created_at)",
        "CREATE INDEX idx_status_created ON opportunity_history(status, created_at)",
        "CREATE INDEX idx_signal_strength ON opportunity_history(signal_strength DESC)"
    ]
    
    for index_query in indexes:
        try:
            self.db.execute_sync_query(index_query)
            print(f"索引创建成功: {index_query}")
        except Exception as e:
            print(f"索引创建失败: {e}")
```

### 2. 分区表设计

```python
# 按时间分区的策略结果表
class PartitionedStrategyResult:
    """分区策略结果表"""
    
    def get_schema(self):
        return {
            "name": "strategy_result",
            "primaryKey": "id",
            "partitionBy": "RANGE (YEAR(created_at))",
            "partitions": [
                {"name": "p2023", "value": "2024"},
                {"name": "p2024", "value": "2025"},
                {"name": "p2025", "value": "2026"}
            ],
            "fields": [
                # ... 字段定义
            ]
        }
```

## 测试和验证

### 1. 单元测试

```python
# tests/test_opportunity_history.py
import unittest
from unittest.mock import Mock, patch
from .tables.opportunity_history.opportunity_history_service import OpportunityHistoryService

class TestOpportunityHistoryService(unittest.TestCase):
    
    def setUp(self):
        self.service = OpportunityHistoryService()
        self.service.db = Mock()
    
    def test_create_opportunity(self):
        """测试创建机会记录"""
        # 模拟数据库连接
        self.service.db.connect_sync.return_value = None
        self.service.db.execute_sync_query.return_value = 1
        
        result = self.service.service.create_opportunity(
            ts_code='000001.SZ',
            signal_type='BUY',
            signal_strength=0.8,
            price=10.50
        )
        
        self.assertEqual(result, 1)
        self.service.db.execute_sync_query.assert_called_once()
    
    def test_get_opportunities_by_stock(self):
        """测试获取股票机会历史"""
        # 模拟查询结果
        mock_result = [
            {'id': 1, 'ts_code': '000001.SZ', 'signal_type': 'BUY'},
            {'id': 2, 'ts_code': '000001.SZ', 'signal_type': 'SELL'}
        ]
        self.service.db.execute_sync_query.return_value = mock_result
        
        result = self.service.get_opportunities_by_stock('000001.SZ')
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['signal_type'], 'BUY')
```

### 2. 集成测试

```python
# tests/integration/test_strategy_tables.py
class TestStrategyTablesIntegration(unittest.TestCase):
    
    def setUp(self):
        """设置测试环境"""
        self.db = DatabaseManager()
        self.db.connect_sync()
        
        # 创建测试表
        self.create_test_tables()
    
    def tearDown(self):
        """清理测试环境"""
        self.drop_test_tables()
        self.db.disconnect_sync()
    
    def test_full_workflow(self):
        """测试完整工作流程"""
        # 1. 创建机会记录
        service = OpportunityHistoryService()
        opportunity_id = service.create_opportunity(
            ts_code='TEST001.SZ',
            signal_type='BUY',
            signal_strength=0.9,
            price=100.00
        )
        
        # 2. 查询机会记录
        opportunities = service.get_opportunities_by_stock('TEST001.SZ')
        self.assertEqual(len(opportunities), 1)
        self.assertEqual(opportunities[0]['signal_type'], 'BUY')
        
        # 3. 更新机会状态
        service.update_opportunity_status(opportunity_id, 'EXECUTED')
        
        # 4. 验证更新结果
        updated_opportunities = service.get_opportunities_by_stock('TEST001.SZ')
        self.assertEqual(updated_opportunities[0]['status'], 'EXECUTED')
```

## 最佳实践

### 1. 设计原则

- **单一职责**: 每个表只负责一个业务领域
- **数据完整性**: 使用外键约束保证数据一致性
- **性能考虑**: 合理设计索引，避免过度索引
- **扩展性**: 预留扩展字段，支持未来功能

### 2. 命名规范

- **表名**: 使用复数形式，如 `opportunities`
- **字段名**: 使用描述性名称，如 `signal_trigger_time`
- **索引名**: 使用有意义的前缀，如 `idx_`、`uk_`

### 3. 文档维护

- 为每个表编写详细的字段说明
- 记录表的业务用途和更新历史
- 提供使用示例和最佳实践

## 常见问题和解决方案

### 1. 表创建失败

**问题**: 表创建时出现语法错误
**解决**: 检查schema.json格式，确保字段类型和长度正确

### 2. 查询性能差

**问题**: 查询速度慢
**解决**: 分析查询计划，添加合适的索引

### 3. 数据不一致

**问题**: 数据在不同表间不一致
**解决**: 使用事务保证数据一致性，添加数据验证

## 联系支持

如有问题或建议，请查看：
- [utils/db/README.md](../../../utils/db/README.md) - 数据库模块主文档
- [app/analyzer/README.md](../README.md) - 分析器模块文档
- 代码注释和错误日志
