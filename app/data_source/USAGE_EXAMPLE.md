# DataSource 使用示例

## 基本调用方式

### 1. 初始化 DataSourceManager

```python
from app.data_source.data_source_manager import DataSourceManager

# 初始化（可选传入 data_manager 用于数据持久化）
data_source = DataSourceManager(data_manager=None, is_verbose=False)
```

### 2. 获取数据源数据

```python
# 基本调用（异步方法）
result = await data_source.fetch("data_source_name")

# 带上下文参数
result = await data_source.fetch(
    "data_source_name",
    context={"start_date": "20240101", "end_date": "20241231"}
)

# 自动保存到数据库（如果 data_manager 已配置）
result = await data_source.fetch("data_source_name")
# 注意：数据保存由 Handler 在 after_normalize 钩子中自动处理
```

### 3. 实际使用示例

```python
import asyncio
from app.data_source.data_source_manager import DataSourceManager

async def main():
    # 初始化
    data_source = DataSourceManager()
    
    # 获取最新交易日
    result = await data_source.fetch("latest_trading_date")
    print(f"最新交易日: {result['data'][0]['date']}")
    
    # 获取股票列表
    result = await data_source.fetch("stock_list")
    stocks = result.get("data", [])
    print(f"股票数量: {len(stocks)}")
    
    # 获取 GDP 数据（需要日期范围）
    result = await data_source.fetch(
        "gdp",
        context={
            "start_date": "2020Q1",
            "end_date": "2024Q4"
        }
    )
    gdp_data = result.get("data", [])
    print(f"GDP 数据条数: {len(gdp_data)}")
    
    # 获取 CPI 数据（月度）
    result = await data_source.fetch(
        "cpi",
        context={
            "start_date": "202401",
            "end_date": "202412"
        }
    )
    cpi_data = result.get("data", [])
    print(f"CPI 数据条数: {len(cpi_data)}")
    
    # 获取 Shibor 数据（日度）
    result = await data_source.fetch(
        "shibor",
        context={
            "start_date": "20240101",
            "end_date": "20241231"
        }
    )
    shibor_data = result.get("data", [])
    print(f"Shibor 数据条数: {len(shibor_data)}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 4. 便捷方法

```python
# 获取股票列表（便捷方法）
stocks = await data_source.get_stock_list()

# 列出所有可用的数据源
available_sources = data_source.list_data_sources()
print(f"可用数据源: {available_sources}")

# 获取数据源的 Schema
schema = data_source.get_schema("gdp")
print(f"GDP Schema: {schema.description}")
```

## 返回数据格式

所有 `fetch` 方法返回的数据格式统一为：

```python
{
    "data": [
        {
            # 根据 Schema 定义的字段
            "field1": value1,
            "field2": value2,
            ...
        },
        ...
    ]
}
```

## 可用的数据源名称

- `latest_trading_date` - 最新交易日
- `stock_list` - 股票列表
- `gdp` - GDP 数据（季度）
- `cpi` - CPI 价格指数（月度）
- `ppi` - PPI 价格指数（月度）
- `pmi` - PMI 采购经理人指数（月度）
- `shibor` - Shibor 利率（日度）
- `lpr` - LPR 利率（日度）
- `money_supply` - 货币供应量（月度）
- `corporate_finance` - 企业财务数据（季度）

## 注意事项

1. **异步方法**：`fetch` 是异步方法，需要使用 `await` 或在异步函数中调用
2. **数据源名称**：使用数据源名称（如 "gdp"），不是模型名称
3. **日期格式**：
   - 日度数据：`YYYYMMDD`（如 "20241209"）
   - 月度数据：`YYYYMM`（如 "202412"）
   - 季度数据：`YYYYQ[1-4]`（如 "2024Q4"）
4. **上下文参数**：某些数据源需要 `context` 参数（如日期范围），某些可以自动计算

