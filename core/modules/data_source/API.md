# Data Source API 文档

**版本：** `0.4.0`  
**最低支持核心版本：** `>=0.3.3`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。

**公开约定：** 包根仅导出 `DataSourceManager`；`BaseProvider` / `BaseHandler` / `ApiJob` 从 [`contracts.py`](./contracts.py) 导入。

---

## DataSourceManager

**描述：** 配置驱动的数据抓取与 renew 编排

### renew / resolve_renew_target / execute

- **状态：** `stable`
- **描述：** CLI / 脚本统一 renew 入口；按依赖拓扑调度 handler

**举例：**

```python
from core.modules.data_source import DataSourceManager

DataSourceManager().renew(table_name="sys_stock_klines")
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `BaseProvider` | 外部 API Provider 基类 |
| `BaseHandler` | 数据源 Handler 基类（`execute` 主入口） |
| `ApiJob` / `ApiJobBundle` | 抓取 job 契约 |

Handler 阶段方法与钩子以 `base_class/base_handler.py` 为准。
