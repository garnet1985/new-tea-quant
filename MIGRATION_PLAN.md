# DataLoader 迁移计划

## 📋 目标

将所有分散的数据加载逻辑统一迁移到新的 `DataLoader`，实现：
- ✅ 统一的API接口
- ✅ 更好的代码组织
- ✅ 便捷方法（零配置）
- ✅ 多进程支持

---

## 🎯 迁移清单

### ✅ 已完成

| 文件 | 状态 | 说明 |
|-----|------|-----|
| `app/analyzer/components/base_strategy.py` | ✅ 已迁移 | 使用新DataLoader |
| `app/analyzer/components/simulator/services/simulating_service.py` | ✅ 已迁移 | 使用新DataLoader |

---

### 🔄 待迁移

#### 1. BFF API (`bff/api.py`)

**当前代码：**
```python
# 获取K线数据
stock_kline_table = db_manager.get_table_instance("stock_kline")
kline_data = stock_kline_table.get_all_k_lines_by_term(stock_id, term, order='ASC')

# 获取复权因子
adj_factor_table = db_manager.get_table_instance("adj_factor")
qfq_factors = adj_factor_table.get_stock_factors(stock_id)

# 应用前复权
data_source_service = DataSourceService()
qfq_kline_data = data_source_service.to_qfq(kline_data, qfq_factors)

# 过滤负价格
qfq_kline_data = [record for record in qfq_kline_data if record['close'] > 0]
```

**迁移后：**
```python
from app.data_loader import DataLoader

# 一行搞定！
loader = DataLoader(db_manager)
qfq_kline_data = loader.load_daily_qfq(stock_id)  # 或 load_monthly_qfq

# 如果需要自定义
qfq_kline_data = loader.load_klines(
    stock_id=stock_id,
    term=term,
    adjust='qfq',
    filter_negative=True
)
```

**优势：**
- ✅ 从 ~10行 减少到 1-2行
- ✅ 自动处理复权和过滤
- ✅ 语义更清晰

---

#### 2. 对比工具 (`tools/compare_qfq_quarterly.py`)

**当前代码：**
```python
k_lines = load_daily_k_lines(db, ts_code, start_date, end_date)
factors = load_qfq_factors(db, ts_code, start_date, end_date)

k_lines_copy = [dict(x) for x in k_lines]
our_qfq_lines = DataSourceService.to_qfq(k_lines_copy, factors)
```

**迁移后：**
```python
from app.data_loader import DataLoader

loader = DataLoader(db)
our_qfq_lines = loader.load_klines(
    stock_id=ts_code,
    term='daily',
    start_date=start_date,
    end_date=end_date,
    adjust='qfq',
    filter_negative=False  # 保留所有数据用于对比
)
```

**优势：**
- ✅ 不需要手动加载factors
- ✅ 不需要手动调用to_qfq
- ✅ 代码更简洁

---

### ⚠️ 不需要迁移（工具方法）

以下文件使用的是 `DataSourceService` 的日期工具方法（不是数据加载），无需迁移：

| 文件 | 使用方法 | 说明 |
|-----|---------|-----|
| `app/data_source/providers/tushare/base_renewer.py` | `time_gap_by`, `to_next` | 日期计算工具 |
| `app/data_source/providers/tushare/renewers/stock_kline/renewer.py` | `get_previous_week_end`, `get_previous_month_end` | 日期计算工具 |
| `app/data_source/providers/akshare/main.py` | `to_hyphen_date_type` | 日期格式转换 |
| `app/data_source/providers/akshare/akshare_API_mod.py` | `parse_ts_code` | 股票代码解析 |

**原因**：这些是底层工具方法，与数据加载无关，保持现状即可。

---

## 📝 迁移步骤

### Phase 1: 迁移 BFF API

1. **备份原文件**
   ```bash
   cp bff/api.py bff/api.py.backup
   ```

2. **修改代码**
   - 导入新的 DataLoader
   - 替换 K线加载逻辑
   - 删除手动复权和过滤代码

3. **测试验证**
   ```bash
   # 启动BFF服务
   python start_bff.py
   
   # 测试API
   curl http://localhost:5000/api/kline/000001.SZ/daily
   ```

4. **确认无问题后删除备份**

---

### Phase 2: 迁移对比工具

1. **备份原文件**
   ```bash
   cp tools/compare_qfq_quarterly.py tools/compare_qfq_quarterly.py.backup
   ```

2. **修改代码**
   - 导入新的 DataLoader
   - 替换数据加载逻辑
   - 删除 `load_daily_k_lines` 和 `load_qfq_factors` 函数

3. **测试验证**
   ```bash
   python tools/compare_qfq_quarterly.py --stock 000001.SZ --start 20230101 --end 20231231
   ```

4. **确认无问题后删除备份**

---

## 🗑️ 淘汰计划

完成迁移后，以下代码可以淘汰（标记为deprecated）：

### DataSourceService 中的数据加载方法

**标记为 Deprecated：**
```python
# app/data_source/data_source_service.py

@staticmethod
@deprecated("Use DataLoader.load_klines() instead")
def to_qfq(k_lines: list, qfq_factors: list):
    """⚠️ 已弃用，请使用 DataLoader.load_klines()"""
    pass

@staticmethod
@deprecated("Use DataLoader.load_klines(filter_negative=True) instead")
def filter_out_negative_records(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """⚠️ 已弃用，请使用 DataLoader.load_klines(filter_negative=True)"""
    pass
```

**保留的工具方法（不淘汰）：**
- `date_to_quarter()`
- `quarter_to_date()`
- `time_gap_by()`
- `to_next()`
- `get_previous_week_end()`
- `get_previous_month_end()`
- `to_hyphen_date_type()`
- `parse_ts_code()`

---

## ✅ 验证清单

完成迁移后，确认以下项目：

- [ ] BFF API 正常返回K线数据
- [ ] BFF API 复权数据正确
- [ ] 对比工具输出结果一致
- [ ] analyzer 和 simulator 仍然正常工作
- [ ] 所有测试通过
- [ ] 删除所有备份文件
- [ ] 更新相关文档

---

## 📊 预期收益

| 指标 | Before | After | 改善 |
|-----|--------|-------|-----|
| 代码行数（单个加载逻辑） | ~10行 | 1-2行 | 80-90%减少 |
| API复杂度 | 需要了解3个模块 | 只需DataLoader | 简化 |
| 维护成本 | 分散，难以统一 | 集中，易于维护 | 显著降低 |
| 新功能开发 | 每次重复实现 | 复用现有方法 | 快速 |

---

## 🚀 后续优化

完成迁移后，可以考虑：

1. **添加更多便捷方法**
   - `load_hfq_klines()` - 后复权快捷方法
   - `load_klines_range()` - 日期范围快捷方法

2. **添加缓存支持**
   - 热点数据缓存
   - 减少重复查询

3. **添加批量加载**
   - `load_multiple_stocks()` - 批量加载多只股票
   - 并行优化

4. **性能监控**
   - 记录加载时间
   - 优化慢查询

---

## 📝 注意事项

1. **向后兼容**：旧代码仍能工作，逐步迁移
2. **测试先行**：每次迁移前先测试新方法
3. **备份重要**：修改前务必备份
4. **逐步淘汰**：先标记deprecated，给用户缓冲期
5. **文档同步**：更新所有相关文档

---

## 📞 需要帮助？

如有问题，参考：
- `app/data_loader/README.md` - DataLoader完整文档
- 已迁移的文件作为示例（base_strategy.py, simulating_service.py）
