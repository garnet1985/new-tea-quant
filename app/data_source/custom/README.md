# 用户自定义区域

本文件夹供用户完全控制，可以自由添加、修改、删除。

## 自定义 Handler

1. 在 `handlers/` 文件夹中创建你的 handler
2. 继承 `BaseHandler` 类
3. 实现 `fetch_and_normalize()` 方法
4. 在 `mapping.json` 中配置使用你的 handler

## 示例

```python
# custom/handlers/my_handler.py
from app.data_source.base_handler import BaseHandler

class MyHandler(BaseHandler):
    async def fetch_and_normalize(self, context):
        # 你的实现
        # 可以使用多个 provider
        # 可以处理复杂的依赖关系
        return data
```

```json
// custom/mapping.json
{
    "data_sources": {
        "stock_list": {
            "handler": "custom.handlers.my_handler.MyHandler",
            "type": "refresh"
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
# custom/schemas.py
from app.data_source.defaults.schemas import DataSourceSchema, Field

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

