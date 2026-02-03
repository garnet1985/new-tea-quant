# Kline Handler 架构方案对比

## 方案对比：一个 Data Source vs 三个 Data Source

### 方案 1：一个 Data Source（当前方案）

**结构**：
```
kline/
  ├── config.py (包含 3 个 API: daily_kline, weekly_kline, monthly_kline)
  ├── handler.py (处理 3 个 API，按股票逐个保存)
  └── schema.py (sys_stock_klines 表，包含 term 字段)
```

**优点**：
1. ✅ **数据逻辑统一**：K 线数据在业务上是一个整体概念
2. ✅ **共享保存逻辑**：`on_after_execute_job_batch_for_single_stock` 可以统一处理
3. ✅ **配置集中**：一个配置文件管理所有周期
4. ✅ **数据一致性**：可以保证同一股票的不同周期数据同时更新
5. ✅ **减少重复代码**：字段映射、数据处理逻辑只需写一次

**缺点**：
1. ❌ **框架支持不足**：需要约 100+ 行自定义代码
2. ❌ **复杂度高**：`on_before_fetch` 需要处理多周期逻辑
3. ❌ **难以独立控制**：无法单独启用/禁用某个周期
4. ❌ **更新策略耦合**：不同周期的更新规则混在一起

**代码量**：
- Handler: ~420 行（包含大量自定义逻辑）
- Config: ~80 行（3 个 API 配置）

---

### 方案 2：拆分成三个 Data Source

**结构**：
```
kline_daily/
  ├── config.py (只有 daily_kline API)
  ├── handler.py (简化的 handler)
  └── schema.py (sys_stock_klines 表，但只处理 daily)

kline_weekly/
  ├── config.py (只有 weekly_kline API)
  ├── handler.py (简化的 handler)
  └── schema.py (sys_stock_klines 表，但只处理 weekly)

kline_monthly/
  ├── config.py (只有 monthly_kline API)
  ├── handler.py (简化的 handler)
  └── schema.py (sys_stock_klines 表，但只处理 monthly)
```

**优点**：
1. ✅ **框架支持好**：每个 data source 独立处理，无需自定义代码
2. ✅ **代码简单**：每个 handler 只需 ~50 行（使用 BaseHandler 标准流程）
3. ✅ **独立控制**：可以单独启用/禁用某个周期
4. ✅ **独立配置**：每个周期可以有不同的 `renew_mode`、`renew_if_over_days` 等
5. ✅ **易于维护**：修改某个周期不影响其他周期

**缺点**：
1. ❌ **配置重复**：3 个配置文件，字段映射等需要重复配置
2. ❌ **代码重复**：保存逻辑、字段映射等需要重复实现（或提取到基类）
3. ❌ **数据一致性**：无法保证同一股票的不同周期数据同时更新
4. ❌ **管理复杂度**：需要管理 3 个 data source 的依赖关系

**代码量**：
- Handler: 3 × ~50 行 = ~150 行（但更简单）
- Config: 3 × ~30 行 = ~90 行（但有重复）

---

## 详细对比

### 1. 框架支持度

| 功能 | 方案 1（一个） | 方案 2（三个） |
|------|---------------|---------------|
| 日期范围配置 | ❌ 需要自定义代码 | ✅ 框架原生支持 |
| 更新规则配置 | ❌ 需要自定义代码 | ✅ 框架原生支持 |
| 多字段分组 | ✅ 已支持 | ✅ 不需要（单字段即可） |
| 按股票保存 | ✅ 通过钩子实现 | ✅ 框架标准流程 |

**结论**：方案 2 的框架支持度更高（10/10 vs 6/10）

### 2. 代码复杂度

| 方面 | 方案 1（一个） | 方案 2（三个） |
|------|---------------|---------------|
| Handler 代码 | ~420 行（复杂） | 3 × ~50 行（简单） |
| Config 代码 | ~80 行 | 3 × ~30 行 |
| 自定义逻辑 | 100+ 行 | 0 行（使用框架） |
| 维护难度 | 高（逻辑集中） | 低（逻辑分散但简单） |

**结论**：方案 2 的代码更简单，但需要管理 3 个文件

### 3. 业务逻辑

| 方面 | 方案 1（一个） | 方案 2（三个） |
|------|---------------|---------------|
| 数据一致性 | ✅ 可以保证同时更新 | ❌ 独立更新，可能不一致 |
| 业务语义 | ✅ K 线是一个整体概念 | ⚠️ 拆分成独立概念 |
| 共享逻辑 | ✅ 统一处理 | ❌ 需要提取到基类或工具类 |

**结论**：方案 1 更符合业务语义

### 4. 可维护性

| 方面 | 方案 1（一个） | 方案 2（三个） |
|------|---------------|---------------|
| 修改影响范围 | ⚠️ 修改影响所有周期 | ✅ 修改只影响单个周期 |
| 独立控制 | ❌ 无法单独启用/禁用 | ✅ 可以独立控制 |
| 配置管理 | ✅ 集中管理 | ⚠️ 分散管理 |
| 代码复用 | ✅ 逻辑集中 | ❌ 需要提取共享代码 |

**结论**：各有优劣，取决于维护策略

---

## 推荐方案

### 推荐：**方案 2（拆分成三个 Data Source）**

**理由**：

1. **框架支持更好**：充分利用框架能力，减少自定义代码
2. **代码更简单**：每个 handler 只需 ~50 行，易于理解和维护
3. **独立控制**：可以单独启用/禁用某个周期，更灵活
4. **符合框架设计**：框架的设计假设就是"一个 data source 的所有 API 使用相同的日期范围"

**实施建议**：

1. **提取共享逻辑**：
   ```python
   # kline_base.py
   class KlineBaseHandler(BaseHandler):
       """K 线 Handler 基类，提供共享逻辑"""
       
       def _map_kline_fields(self, df, stock_id, api_name):
           # 共享的字段映射逻辑
           pass
       
       def on_after_execute_job_batch_for_single_stock(self, ...):
           # 共享的保存逻辑
           pass
   ```

2. **三个独立的 Handler**：
   ```python
   # kline_daily/handler.py
   class KlineDailyHandler(KlineBaseHandler):
       """日线 Handler"""
       pass  # 使用基类的所有逻辑
   
   # kline_weekly/handler.py
   class KlineWeeklyHandler(KlineBaseHandler):
       """周线 Handler"""
       pass
   
   # kline_monthly/handler.py
   class KlineMonthlyHandler(KlineBaseHandler):
       """月线 Handler"""
       pass
   ```

3. **独立配置**：
   ```python
   # kline_daily/config.py
   CONFIG = {
       "table": "sys_stock_klines",
       "renew": {
           "type": "incremental",
           "last_update_info": {
               "date_field": "date",
               "date_format": DateUtils.PERIOD_DAY,
           },
           "result_group_by": {
               "list": "stock_list",
               "key": "id",  # 单字段分组即可
           },
       },
       "apis": {
           "daily_kline": {
               "provider_name": "tushare",
               "method": "get_daily_kline",
               "max_per_minute": 700,
               "field_mapping": {...},
           },
       },
   }
   ```

**迁移成本**：
- 需要创建 3 个新的 handler 目录
- 提取共享逻辑到基类
- 更新 mapping.py 配置
- 测试验证

**预期收益**：
- 代码量减少：~420 行 → ~150 行（3 × 50）
- 自定义代码减少：100+ 行 → 0 行
- 框架支持度提升：6/10 → 10/10

---

## 对比总结

| 维度 | 方案 1（一个） | 方案 2（三个） | 推荐 |
|------|---------------|---------------|------|
| 框架支持 | 6/10 | 10/10 | ✅ 方案 2 |
| 代码复杂度 | 高 | 低 | ✅ 方案 2 |
| 业务语义 | 好 | 一般 | ✅ 方案 1 |
| 可维护性 | 一般 | 好 | ✅ 方案 2 |
| **综合** | **6/10** | **9/10** | **✅ 方案 2** |

**最终建议**：拆分成三个 Data Source，通过基类共享逻辑，既利用了框架能力，又保持了代码的简洁性。
