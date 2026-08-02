# Data Manager API 文档

**版本：** `0.4.0`  
**最低支持核心版本：** `>=0.4.1`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。

**公开约定：** 包根仅导出 `DataManager`；`BaseTableNames` 从 [`contracts.py`](./contracts.py) 导入。  
**CalendarService：** 经 `DataManager.calendar` 访问，不从包根导出。

---

## DataManager

**描述：** 统一数据访问门面

### __init__ / initialize

- **状态：** `stable`
- **描述：** 构造时幂等 `initialize()`；默认进程内单例

### get_table / register_table

- **状态：** `stable`

### 领域服务（属性）

| 属性 | 说明 |
|------|------|
| `stock` | K 线、列表、指标、tag 等 |
| `macro` | 宏观序列 |
| `calendar` | 交易日历（CalendarService） |
| `index` | 指数 |
| `db_cache` | 仿真缓存表 |

**举例：**

```python
from core.modules.data_manager import DataManager

dm = DataManager(is_verbose=True)
klines = dm.stock.kline.load("000001.SZ", term="daily", adjust="qfq")
open_dates = dm.calendar.load_open_dates("20240101", "20241231")
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `BaseTableNames` | 基础表名枚举（内部/扩展用） |
