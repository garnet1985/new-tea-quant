# 数据迁移：旧表 → sys_* 新表 清单

本文档列出「旧库表名 / 数据来源」到「新 sys_* 表」的迁移对应关系，用于实现迁移脚本时逐项完成。

---

## 1. 一对一迁移（表名变更，结构基本一致）

| 序号 | 旧表名（或 base_tables 对应表） | 迁移到新表 | 说明 |
|-----|--------------------------------|------------|------|
| 1 | `stock_list` | `sys_stock_list` | 字段对齐；若有 industry 列，可选同时写入 sys_industries + sys_stock_industries（见 4） |
| 2 | `adj_factor_event` | `sys_adj_factor_events` | 新表名为复数 events，字段按新 schema 对齐 |
| 3 | `corporate_finance` | `sys_corporate_finance` | 字段按新 schema 对齐 |
| 4 | `gdp` | `sys_gdp` | 字段按新 schema 对齐 |
| 5 | `lpr` | `sys_lpr` | 字段按新 schema 对齐 |
| 6 | `shibor` | `sys_shibor` | 字段按新 schema 对齐 |
| 7 | `stock_index_indicator` | `sys_stock_index_indicator` | 字段按新 schema 对齐 |
| 8 | `stock_index_indicator_weight` | `sys_stock_index_indicator_weight` | 字段按新 schema 对齐 |
| 9 | `system_cache` | `sys_cache` | 字段按新 schema 对齐 |
| 10 | `tag_scenario` | `sys_tag_scenario` | 字段按新 schema 对齐 |
| 11 | `tag_definition` | `sys_tag_definition` | 字段按新 schema 对齐 |
| 12 | `tag_value` | `sys_tag_value` | 字段按新 schema 对齐 |
| 13 | `meta_info` | `sys_meta_info` | 字段按新 schema 对齐 |
| 14 | `investment_operations` | `sys_investment_operations` | 若新表已存在则迁移；否则先加表再迁 |
| 15 | `investment_trades` | `sys_investment_trades` | 若新表已存在则迁移；否则先加表再迁 |

---

## 2. 一拆多：K 线（按 term 拆成三张表）

| 序号 | 旧表名 | 迁移到新表 | 说明 |
|-----|--------|------------|------|
| 16 | `stock_kline` | `sys_stock_kline_daily` | 仅 `term = 'daily'` 的 K 线行；去掉 term 列，只保留 id/date/open/close/最高最低/量等 |
| 17 | `stock_kline` | `sys_stock_kline_weekly` | 仅 `term = 'weekly'` 的 K 线行 |
| 18 | `stock_kline` | `sys_stock_kline_monthly` | 仅 `term = 'monthly'` 的 K 线行 |

---

## 3. 一拆多：K 线中的 daily_basic → 指标表

| 序号 | 旧表名 / 数据来源 | 迁移到新表 | 说明 |
|-----|-------------------|------------|------|
| 19 | `stock_kline`（daily 行中的 daily_basic 相关列） | `sys_stock_indicators` | 从旧表 daily 数据中抽取 pe、pb、turnover 等指标列，按 id+date 写入 sys_stock_indicators |

---

## 4. 一拆多：价格指数（原单表按类型拆四张）

| 序号 | 旧表名 | 迁移到新表 | 说明 |
|-----|--------|------------|------|
| 20 | `price_indexes` | `sys_cpi` | 抽取 cpi、cpi_yoy、cpi_mom、date 等列 |
| 21 | `price_indexes` | `sys_ppi` | 抽取 ppi、ppi_yoy、ppi_mom、date 等列 |
| 22 | `price_indexes` | `sys_pmi` | 抽取 pmi、pmi_l_scale、pmi_m_scale、pmi_s_scale、date 等列 |
| 23 | `price_indexes` | `sys_money_supply` | 抽取 m0/m1/m2 及 yoy、mom、date 等列 |

---

## 5. 衍生：行业表（来自 stock_list.industry）

| 序号 | 旧表名 / 数据来源 | 迁移到新表 | 说明 |
|-----|-------------------|------------|------|
| 24 | `stock_list`（industry 列） | `sys_industries` | 对 industry 去重，生成 id（如自增或哈希）、value（行业名）、is_alive |
| 25 | `stock_list`（id + industry） | `sys_stock_industries` | 每条 (stock_id, industry_id) 对应 stock_list 一行中的 id 与 该行 industry 在 sys_industries 中的 id |

若旧表无 industry 列或为空，可只建空表，后续由 stock list 的 data source renew 填充。

---

## 6. 迁移顺序建议（减少外键/依赖）

1. **无依赖**：sys_gdp, sys_lpr, sys_shibor, sys_cpi, sys_ppi, sys_pmi, sys_money_supply, sys_cache, sys_meta_info, sys_tag_scenario, sys_tag_definition  
2. **行业**：sys_industries → sys_stock_industries（若从 stock_list 推导）  
3. **股票基础**：sys_stock_list（若拆 industry 则先 24、25 再本表或同时写）  
4. **K 线**：sys_stock_kline_daily / weekly / monthly  
5. **K 线衍生**：sys_stock_indicators（依赖 daily 的 id+date）  
6. **其余**：sys_adj_factor_events, sys_corporate_finance, sys_stock_index_indicator, sys_stock_index_indicator_weight, sys_tag_value, sys_investment_operations, sys_investment_trades（若存在）

---

## 7. 实现状态（打勾表示已完成）

- [x] 迁移脚本已实现：`scripts/migrate_to_sys_tables.py`（涵盖 1–25 项）
- [ ] 1–15 一对一迁移（脚本就绪，需确保各 model 的 schema 导入路径与 `core/tables/<category>/<table_name>/` 一致后方可完整执行）
- [ ] 16–18 K 线按 term 拆三表  
- [ ] 19 K 线 daily_basic → sys_stock_indicators  
- [ ] 20–23 price_indexes 拆四表  
- [ ] 24–25 行业衍生 sys_industries + sys_stock_industries  

迁移脚本已实现：`scripts/migrate_to_sys_tables.py`，按上表逐项从旧表读取、转换后调用 `data_manager.get_table("sys_xxx")` 写入新表。执行前请先运行 `scripts/create_sys_tables.py` 创建新表。可选 `MIGRATE_DRY_RUN=1` 仅检查并统计不写入。
