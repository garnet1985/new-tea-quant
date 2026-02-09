# K 线按 term 存一张表 vs 按 term 分表

当前：所有周期（daily / weekly / monthly）的 K 线存在 **一张表 `stock_kline`**，用 **`term` 列** 区分。  
可选：按周期拆成 **三张表**（如 `kline_daily` / `kline_weekly` / `kline_monthly`），每张表无 `term` 列。

---

## 1. 当前形态（一张表 + term 列）

- **表**：`stock_kline`，主键 `(id, term, date)`，索引含 `(id, term, date)`、`(id, term)` 等。
- **读**：几乎都是「按周期读」——`load_raw(stock_id, term, ...)`、`load_qfq(stock_id, term, ...)`，WHERE 里都有 `term = %s`。
- **写**：renew 已是按 (stock, term) 算 last_update，写入时带 `term`。
- **数据量**：同一只股票有 daily + weekly + monthly，行数约为「只存 daily」的约 3 倍（周/月行数少，实际不到 3 倍但同一表混合）。

**优点**  
- 已跑在生产，无需迁移。  
- 一张表、一套 schema、一个 data source（若坚持一 data source 一表，可保留一个「kline」data source 写这一张表）。  
- 需要「多周期一起」时（如 `load_by_settings(terms=[daily, weekly])`）一次查询 `WHERE id=? AND term IN (...)` 即可。

**缺点**  
- 表内混合三种周期，单次「只要日线」的查询也会扫到周/月行（有 `(id, term, date)` 索引时影响不大）。  
- schema 里必须带 `term`；若后续严格「一表一 schema、schema 即实体」，则「K 线」实体要带 term，不如「日线实体 = 日线表」直观。

---

## 2. 按 term 分表（三张表，无 term 列）

- **表**：`kline_daily`、`kline_weekly`、`kline_monthly`，主键均为 `(id, date)`，schema 相同且**无** `term` 列。
- **读**：要日线 → 只查 `kline_daily`；要周线 → 只查 `kline_weekly`。  
- **写**：三个 data source（或一个 Handler 写三张表）分别写三张表；renew 仍是 per (stock, term)，对应到三张表的 last_update 即可。
- **数据量**：每张表约为当前单表行数的 1/3（按周期拆分），单表更小。

**优点**  
- 与「一 data source 一表、schema = 表」一致：一个周期 = 一张表 = 一个 schema，无需 `term` 列。  
- 读 99% 是「按周期」的，分表后只扫对应表，语义清晰、单表更小，便于以后按表做分区/备份。  
- 每张表的主键就是 `(id, date)`，更简单。

**缺点**  
- 需要迁移：表结构拆分 + 数据迁移 + KlineService 等改为按表名路由（如 `get_table('kline_daily')` 等）。  
- 需要「多周期一起」时（如 load_by_settings 要 daily+weekly）：查两张表再在应用层拼，多一次 round-trip；若这类需求少，影响不大。

---

## 3. 对比小结

| 项目 | 一张表 + term | 按 term 分三张表 |
|------|----------------|------------------|
| **表结构** | 主键 (id, term, date)，有 term 列 | 每表主键 (id, date)，无 term 列 |
| **读** | 每次 WHERE term=?，有合适索引即可 | 按表查，只扫该周期数据 |
| **写 / renew** | 已支持 per (stock, term) | 每表独立 last_update，自然 per term |
| **与「一 data source 一表」** | 一个 data source 写一张表，可接受 | 三个 data source 写三张表，完全对齐 |
| **多周期一次查** | 一次查询 term IN (...) | 需查多表再合并 |
| **迁移** | 无 | 需要 |

---

## 4. 建议

- **若近期不打算大改 K 线 + 不做「按周期分 data source」**：**维持一张表即可**。  
  - 现有 `(id, term, date)` 索引下，按 term 的查询已经合理；renew 也是按 (stock, term) 的，没有结构性瓶颈。  
  - 保持现状成本最低。

- **若已在做「per-table data source + schema = 表 + Entity」**：**更建议按 term 分表**。  
  - 一个周期一张表、无 `term` 列，和「一 schema 一表」一致，语义更清晰。  
  - 读路径几乎都是按周期，分表后更贴近期望用法，单表更小，后续分区/维护更简单。  
  - 多周期一起查的场景（如 load_by_settings 要多 term）相对少，多查一两次表可接受。

**结论**：  
- **不改架构、求稳** → **一张表 + term 没问题**，保持即可。  
- **统一到 per-table、schema=表** → **按 term 分三张表更一致、更利于长期**，在合适时机做迁移即可。
