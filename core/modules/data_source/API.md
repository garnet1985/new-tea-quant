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

Handler 阶段钩子以实现为准；生产代码勿 deep-import `service/` / `catalog/`。
