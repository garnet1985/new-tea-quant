# 默认 DataSource、Schema 和 Handler

本文件夹包含框架默认提供的实现，**不应修改**。

## 默认 DataSource

- `stock_list` - 股票列表
- `daily_kline` - 日线数据
- `weekly_kline` - 周线数据
- `monthly_kline` - 月线数据
- `corporate_finance` - 财务数据
- `gdp` - GDP 数据
- `cpi` - CPI 数据
- `ppi` - PPI 数据
- `pmi` - PMI 数据
- `shibor` - Shibor 数据
- `lpr` - LPR 数据
- `money_supply` - 货币供应量数据
- `adj_factor` - 复权因子

## 使用默认 Handler

在 `custom/mapping.json` 中配置：

```json
{
    "data_sources": {
        "stock_list": {
            "handler": "defaults.handlers.stock_list_handler.TushareStockListHandler",
            "type": "refresh"
        }
    }
}
```

## 扩展

如果需要自定义，请在 `custom/` 文件夹中实现。

