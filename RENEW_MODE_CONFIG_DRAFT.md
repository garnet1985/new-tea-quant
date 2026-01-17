# Renew Mode 配置草稿

## 设计说明

### Renew Mode 类型
- `incremental`: 从最新日期到当前（增量更新）
- `rolling`: 滚动刷新（每次刷新最近 N 个时间单位）
- `refresh`: 全量刷新（使用 default_date_range）

### Date Format 类型
- `quarter`: 季度数据（YYYYQ[1-4]）
- `month`: 月度数据（YYYYMM）
- `date`: 日期数据（YYYYMMDD）
- `none`: 不需要日期

### Rolling 配置
- `rolling_unit`: 滚动单位（"quarter" | "month" | "day"）
- `rolling_length`: 每个滚动单位的长度（int，如 4 表示 4 个季度）

### Table 信息
- `table_name`: 数据库表名（用于查询最新日期）
- `date_field`: 数据库日期字段名（用于查询最新日期）
- 注意：Refresh mode 不需要 table 信息

---

## 所有 Handler 的配置草稿

### 1. gdp (GDP 数据)

```json
{
  "gdp": {
    "handler": "userspace.data_source.handlers.gdp.GdpHandler",
    "is_enabled": true,
    "provider_config": {
      "apis": [
        {
          "provider_name": "tushare",
          "method": "get_gdp",
          "field_mapping": {
            "quarter": "quarter",
            "gdp": "gdp",
            "gdp_yoy": "gdp_yoy",
            "primary_industry": "pi",
            "primary_industry_yoy": "pi_yoy",
            "secondary_industry": "si",
            "secondary_industry_yoy": "si_yoy",
            "tertiary_industry": "ti",
            "tertiary_industry_yoy": "ti_yoy"
          },
          "params": {}
        }
      ]
    },
    "handler_config": {
      "renew_mode": "rolling",
      "date_format": "quarter",
      "rolling_unit": "quarter",
      "rolling_length": 4,
      "default_date_range": {"years": 5},
      "table_name": "gdp",
      "date_field": "quarter"
    }
  }
}
```

### 2. shibor (Shibor 数据)

```json
{
  "shibor": {
    "handler": "userspace.data_source.handlers.shibor.ShiborHandler",
    "is_enabled": true,
    "provider_config": {
      "apis": [
        {
          "provider_name": "tushare",
          "method": "get_shibor",
          "field_mapping": {
            "date": "date",
            "one_night": "on",
            "one_week": "1w",
            "one_month": "1m",
            "three_month": "3m",
            "one_year": "1y"
          },
          "params": {}
        }
      ]
    },
    "handler_config": {
      "renew_mode": "rolling",
      "date_format": "date",
      "rolling_unit": "day",
      "rolling_length": 30,
      "default_date_range": {"years": 1},
      "table_name": "shibor",
      "date_field": "date"
    }
  }
}
```

### 3. lpr (LPR 数据)

```json
{
  "lpr": {
    "handler": "userspace.data_source.handlers.lpr.LprHandler",
    "is_enabled": true,
    "provider_config": {
      "apis": [
        {
          "provider_name": "tushare",
          "method": "get_lpr",
          "field_mapping": {
            "date": "date",
            "lpr_1_y": "1y",
            "lpr_5_y": "5y"
          },
          "params": {}
        }
      ]
    },
    "handler_config": {
      "renew_mode": "rolling",
      "date_format": "date",
      "rolling_unit": "day",
      "rolling_length": 30,
      "default_date_range": {"years": 1},
      "table_name": "lpr",
      "date_field": "date"
    }
  }
}
```

### 4. price_indexes (价格指数数据)

```json
{
  "price_indexes": {
    "handler": "userspace.data_source.handlers.price_indexes.PriceIndexesHandler",
    "is_enabled": true,
    "provider_config": {
      "apis": [
        {
          "provider_name": "tushare",
          "method": "get_cpi",
          "field_mapping": {...},
          "params": {}
        },
        {
          "provider_name": "tushare",
          "method": "get_ppi",
          "field_mapping": {...},
          "params": {}
        },
        {
          "provider_name": "tushare",
          "method": "get_pmi",
          "field_mapping": {...},
          "params": {}
        },
        {
          "provider_name": "tushare",
          "method": "get_money_supply",
          "field_mapping": {...},
          "params": {}
        }
      ]
    },
    "handler_config": {
      "renew_mode": "rolling",
      "date_format": "month",
      "rolling_unit": "month",
      "rolling_length": 12,
      "default_date_range": {"years": 3},
      "table_name": "price_indexes",
      "date_field": "date"
    }
  }
}
```

### 5. kline (K线数据)

```json
{
  "kline": {
    "handler": "userspace.data_source.handlers.kline.KlineHandler",
    "is_enabled": true,
    "provider_config": {
      "apis": []
    },
    "handler_config": {
      "renew_mode": "incremental",
      "date_format": "date",
      "default_date_range": {"years": 5},
      "table_name": "stock_kline_daily",
      "date_field": "date",
      "debug_limit_stocks": null
    }
  }
}
```

**注意**: kline 是复杂的 handler，需要按股票和周期处理，可能需要自定义逻辑，但基础配置可以这样。

### 6. stock_list (股票列表)

```json
{
  "stock_list": {
    "handler": "userspace.data_source.handlers.stock_list.TushareStockListHandler",
    "is_enabled": true,
    "provider_config": {
      "apis": [
        {
          "provider_name": "tushare",
          "method": "get_stock_list",
          "field_mapping": {},
          "params": {
            "fields": "ts_code,symbol,name,area,industry,market,exchange,list_date"
          }
        }
      ]
    },
    "handler_config": {
      "renew_mode": "refresh",
      "date_format": "none",
      "default_date_range": {},
      "api_fields": "ts_code,symbol,name,area,industry,market,exchange,list_date"
    }
  }
}
```

**注意**: refresh 模式不需要 `table_name` 和 `date_field`。

### 7. latest_trading_date (最新交易日)

```json
{
  "latest_trading_date": {
    "handler": "userspace.data_source.handlers.latest_trading_date.LatestTradingDateHandler",
    "is_enabled": true,
    "provider_config": {
      "apis": [
        {
          "provider_name": "tushare",
          "method": "get_trade_cal",
          "field_mapping": {},
          "params": {}
        }
      ]
    },
    "handler_config": {
      "renew_mode": "refresh",
      "date_format": "none",
      "default_date_range": {},
      "backward_checking_days": 15
    }
  }
}
```

**注意**: refresh 模式不需要 `table_name` 和 `date_field`。

### 8. corporate_finance (企业财务数据)

```json
{
  "corporate_finance": {
    "handler": "userspace.data_source.handlers.corporate_finance.CorporateFinanceHandler",
    "is_enabled": true,
    "provider_config": {
      "apis": []
    },
    "handler_config": {
      "renew_mode": "incremental",
      "date_format": "quarter",
      "default_date_range": {"years": 5},
      "table_name": "corporate_finance",
      "date_field": "quarter",
      "rolling_quarters": 3,
      "renew_rolling_batch": 8
    }
  }
}
```

**注意**: 需要按股票处理，有滚动批次逻辑。

### 9. adj_factor_event (复权因子事件)

```json
{
  "adj_factor_event": {
    "handler": "userspace.data_source.handlers.adj_factor_event.AdjFactorEventHandler",
    "is_enabled": true,
    "provider_config": {
      "apis": []
    },
    "handler_config": {
      "renew_mode": "incremental",
      "date_format": "date",
      "default_date_range": {"years": 5},
      "table_name": "adj_factor_event",
      "date_field": "event_date",
      "update_threshold_days": 15,
      "max_workers": 10
    }
  }
}
```

**注意**: 需要按股票处理，有更新阈值逻辑。

### 10. stock_index_indicator (股指指标)

```json
{
  "stock_index_indicator": {
    "handler": "userspace.data_source.handlers.stock_index_indicator.StockIndexIndicatorHandler",
    "is_enabled": true,
    "provider_config": {
      "apis": []
    },
    "handler_config": {
      "renew_mode": "incremental",
      "date_format": "date",
      "default_date_range": {"years": 5},
      "table_name": "stock_index_indicator",
      "date_field": "date",
      "index_list": [
        {"id": "000001.SH", "name": "上证指数"},
        {"id": "000300.SH", "name": "沪深300"},
        {"id": "000688.SH", "name": "科创50"},
        {"id": "399001.SZ", "name": "深证成指"},
        {"id": "399006.SZ", "name": "创业板指"}
      ]
    }
  }
}
```

**注意**: 需要按指数和周期处理。

### 11. stock_index_indicator_weight (股指成分股权重)

```json
{
  "stock_index_indicator_weight": {
    "handler": "userspace.data_source.handlers.stock_index_indicator_weight.StockIndexIndicatorWeightHandler",
    "is_enabled": true,
    "provider_config": {
      "apis": []
    },
    "handler_config": {
      "renew_mode": "incremental",
      "date_format": "date",
      "default_date_range": {"years": 5},
      "table_name": "stock_index_indicator_weight",
      "date_field": "date",
      "index_list": [
        {"id": "000001.SH", "name": "上证指数"},
        {"id": "000300.SH", "name": "沪深300"},
        {"id": "000688.SH", "name": "科创50"},
        {"id": "399001.SZ", "name": "深证成指"},
        {"id": "399006.SZ", "name": "创业板指"}
      ]
    }
  }
}
```

**注意**: 需要按指数处理。

---

## 配置验证

### ✅ 可以覆盖的需求

1. **Rolling 模式** (4 个 handler):
   - gdp: 季度滚动（4 个季度）
   - shibor: 日期滚动（30 天）
   - lpr: 日期滚动（30 天）
   - price_indexes: 月度滚动（12 个月）

2. **Incremental 模式** (5 个 handler):
   - kline: 日期增量（按股票和周期）
   - corporate_finance: 季度增量（按股票）
   - adj_factor_event: 日期增量（按股票）
   - stock_index_indicator: 日期增量（按指数和周期）
   - stock_index_indicator_weight: 日期增量（按指数）

3. **Refresh 模式** (2 个 handler):
   - stock_list: 全量刷新
   - latest_trading_date: 全量刷新

### ⚠️ 需要注意的点

1. **复杂 Handler 仍需要自定义逻辑**:
   - kline: 需要按股票和周期处理，可能需要自定义 `before_fetch` 和 `fetch`
   - corporate_finance: 需要滚动批次逻辑，可能需要自定义 `before_fetch`
   - adj_factor_event: 需要更新阈值逻辑，可能需要自定义 `before_fetch`
   - stock_index_indicator: 需要按指数和周期处理，可能需要自定义 `before_fetch` 和 `fetch`
   - stock_index_indicator_weight: 需要按指数处理，可能需要自定义 `before_fetch` 和 `fetch`

2. **基础配置可以统一**:
   - 所有 handler 的基础配置（renew_mode, date_format, default_date_range, table_name, date_field）都可以统一
   - 复杂 handler 可以在基础配置之上添加自定义逻辑

3. **自定义参数**:
   - 每个 handler 可能有自己的自定义参数（如 `debug_limit_stocks`, `backward_checking_days`, `index_list` 等）
   - 这些参数可以继续放在 `handler_config` 中

---

## 总结

✅ **所有 handler 都可以用新的 renew_mode 配置覆盖基础需求**

✅ **复杂 handler 仍需要自定义逻辑，但基础配置可以统一**

✅ **设计可以走通，可以开始实施**
