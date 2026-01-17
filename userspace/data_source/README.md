# 用户自定义区域

本文件夹供用户完全控制，可以自由添加、修改、删除。

## 自定义 Handler

1. 在 `handlers/` 文件夹中创建你的 handler
2. 继承 `BaseDataSourceHandler` 类
3. 实现 `fetch()` 和 `normalize()` 方法
4. 在 `mapping.json` 中配置使用你的 handler

## 示例

```python
# userspace/data_source/handlers/my_handler.py
from core.modules.data_source.base_data_source_handler import BaseDataSourceHandler
from core.modules.data_source.api_job import DataSourceTask, ApiJob

class MyHandler(BaseDataSourceHandler):
    data_source = "my_custom_data"
    description = "我的自定义数据源"
    dependencies = []
    
    async def fetch(self, context):
        # 生成 Tasks
        task = self.create_simple_task(
            provider_name="tushare",
            method="get_my_data",
            params={}
        )
        return [task]
    
    async def normalize(self, task_results):
        # 标准化数据
        df = self.get_simple_result(task_results)
        # 处理数据...
        return {"data": [...]}
```

```json
// userspace/data_source/mapping.json
{
    "data_sources": {
        "my_custom_data": {
            "handler": "userspace.data_source.handlers.my_handler.MyHandler",
            "is_enabled": true,
            "dependencies": {
                "latest_completed_trading_date": false,
                "stock_list": false
            },
            "params": {}
        }
    }
}
```

## Handler 可以做什么

- 使用一个或多个 provider
- 处理 provider 之间的依赖关系
- 实现限流、重试、缓存等逻辑
- 合并多个数据源的数据
- 标准化数据为框架 schema

## 自定义 Schema

如果默认 schema 不满足需求，可以在 `schemas.py` 中自定义：

```python
# userspace/data_source/schemas.py
from core.modules.data_source.schemas import DataSourceSchema, Field

MY_CUSTOM_SCHEMA = DataSourceSchema(
    name="my_custom_data",
    description="我的自定义数据",
    schema={
        "field1": Field(str, required=True),
        "field2": Field(float, required=False),
    }
)

CUSTOM_SCHEMAS = {
    "my_custom_data": MY_CUSTOM_SCHEMA,
}
```

