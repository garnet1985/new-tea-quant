# Data Source API 文档

**版本：** `0.4.0`  
**最低支持核心版本：** `>=0.4.1`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `DataSourceManager`；`BaseProvider` / `BaseHandler` / `ApiJob` / `ApiJobBundle` 从 [`contracts.py`](./contracts.py) 导入。

---

## DataSourceManager

**描述：** 配置驱动的数据抓取与 renew 编排

### renew

`DataSourceManager.renew(table_name=None, *, force=False) -> None`

- **状态：** `beta`
- **描述：** CLI / 脚本统一 renew 入口
- **参数：**
  - `table_name`：绑定表名（如 `sys_stock_klines`）或 data source key；`None` = 全部已启用
  - `force`：强制从默认起点重拉，跳过日缓存与 `renew_if_over_days`

### resolve_renew_target

`DataSourceManager.resolve_renew_target(table_or_source) -> str`

- **状态：** `beta`
- **描述：** 表名或 key → mapping 中的 data source key；找不到则 `ValueError`（含可选列表提示）

### list_renew_targets

`DataSourceManager.list_renew_targets() -> List[Dict[str, str]]`

- **状态：** `beta`
- **描述：** 已启用目标列表；每项含 `source`、`table`

### format_renew_targets_help

`DataSourceManager.format_renew_targets_help() -> str`（classmethod）

- **状态：** `beta`
- **描述：** 格式化可选表名 / key，供 CLI 报错提示

### get_data_end_meta / resolve_freshness_end_date

`DataSourceManager.get_data_end_meta(data_manager=None) -> dict`（staticmethod）  
`DataSourceManager.resolve_freshness_end_date(data_manager=None) -> str`（staticmethod）  
`DataSourceManager.get_data_end_meta_light() -> dict`（staticmethod）

- **状态：** `beta`
- **描述：** 数据截断 / 有效结束日（供 scan UI）；对齐 `data.json` as_of 与交易日历。跨模块入口，勿 deep-import `catalog.freshness_probe`

### catalog / provider / sample pool（跨模块辅助）

- **状态：** `beta`
- **描述：** 收口原 `catalog.*` / `sample_stock_list` 深路径；BFF、DM、devtools 请走 Facade
- **常用：**
  - `get_provider` / `discover_provider_classes`
  - `fetch_real_world_latest_completed_trading_date` / `ensure_calendar_real_world_fetcher_registered`
  - `evaluate_update_status` / `summarize_provider_auth` / `min_rate_limit_per_minute`
  - `builtin_source_keys` / `default_display_names`
  - `slice_stock_list` / `sample_pool_count` / `pool_stock_ids` / `default_sample_n` / `pool_csv_path` / `invalidate_pool_cache`
  - `discover_mappings` / `discover_config`（实例方法）

### execute

`DataSourceManager.execute(sources=None, *, force=False)`

- **状态：** `beta`
- **描述：** 发现 mapping/config/handler → 拓扑调度执行。推荐日常用 `renew`；本方法供多源或内部调度
- **参数：**
  - `sources`：仅这些 data source key；`None` = 全部已启用
  - `force`：同 `renew`

**举例：**

```python
from core.modules.data_source import DataSourceManager

mgr = DataSourceManager()
mgr.list_renew_targets()
mgr.renew(table_name="sys_stock_klines")
mgr.renew(table_name="stock_klines", force=True)
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `BaseProvider` | 外部 API Provider 基类 |
| `BaseHandler` | 数据源 Handler 基类 |
| `ApiJob` / `ApiJobBundle` | 抓取 job 契约 |
| `DataSourceConfig` / `ApiConfig` | handler config 契约 |
| `DataSourceField` / `DataSourceSchema` | schema 字段契约 |
| `NormalizationHelper` | handler 规范化工具模块（`apply_field_mapping` / `result_to_records` 等） |
| `UpdateMode` | renew 模式枚举 |

Handler 阶段钩子以实现为准；生产 / userspace 代码勿 deep-import `service/` / `catalog/`。跨模块请用 `DataSourceManager`（含 freshness / sample pool / provider / catalog 辅助）与 `contracts`。
