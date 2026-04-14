# 数据源使用指南

本指南介绍如何开发和使用数据源 Handler 和 Provider。

## 快速开始

### 创建自定义 Handler

参考 [数据源用户指南](../../userspace/data_source/USER_GUIDE.md) 创建自定义 Handler。

### 使用现有 Handler

```python
from core.modules.data_source import DataSourceManager

# 获取 Handler
manager = DataSourceManager()
handler = manager.get_handler("kline")

# 更新数据
await handler.renew()
```

## Handler 开发

### 基本结构

```python
from core.modules.data_source.base_data_source_handler import BaseDataSourceHandler

class MyHandler(BaseDataSourceHandler):
    data_source = "my_data_source"
    description = "我的数据源"
    
    async def fetch(self, context):
        """生成数据获取任务"""
        pass
    
    async def normalize(self, raw_data):
        """标准化数据"""
        pass
```

### Provider 使用

```python
# 获取 Provider
pool = get_provider_pool()
tushare = pool.get_provider("tushare")

# 调用 API
data = await tushare.get_stock_list()
```

## 详细文档

- [数据源用户指南](../../userspace/data_source/USER_GUIDE.md) - 完整教程
- [DataSource 架构](../docs/architecture/data_source_architecture.md) - 架构设计
- [DataSource README](../../core/modules/data_source/README.md) - 详细文档
- [Provider 文档](../../userspace/data_source/providers/README.md) - Provider 开发指南

## 相关文档

- [策略开发指南](strategy-development.md) - 策略中使用数据源
- [架构文档](../docs/architecture/) - 系统架构文档
