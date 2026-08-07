# Utils API 文档

**版本：** `0.2.0`  
**最低支持核心版本：** `>=0.4.0`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。  
> 所列门面入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `Utils`；周期常量可从 [`contracts.py`](./contracts.py) 导入。

---

## Utils

**描述：** 通用无业务工具门面 — `date` / `types` / `io` / `math`

### date

`Utils.date` 绑定内部 `DateUtils` 类（全部 `@staticmethod`）。

常用：

| 方法 | 说明 |
|------|------|
| `today()` | 今日 `YYYYMMDD` |
| `normalize_str` / `normalize` / `to_format` | 解析与格式化 |
| `add_days` / `sub_days` / `diff_days` | 日级运算 |
| `is_before` / `is_after` / `is_same` | 比较 |
| `to_period_str` / `from_period_str` / `add_periods` … | 周期运算 |
| `PERIOD_DAY` / `PERIOD_MONTH` / … | 周期常量 |

- **状态：** `beta`
- **举例：**

```python
from core.infra.utils import Utils

Utils.date.normalize_str("2024-01-15")  # "20240115"
Utils.date.diff_days("20240101", "20240116")
```

### types

`Utils.types` 绑定内部 `TypeUtils`：类型判断、`deep_merge` / `deep_diff`、DataFrame 薄封装。

- **状态：** `beta`

### io

| 方法 | 说明 |
|------|------|
| `write_dicts_to_csv` / `read_csv_to_dicts` | List[dict] ↔ CSV |
| `dicts_to_csv_bytes` / `csv_bytes_to_dicts` | 内存 CSV |
| `write_archive` / `read_archive_files` | zip / tar.gz / csv |

- **状态：** `beta`

### math

`Utils.math.deterministic_unit_float(*key_parts) -> float`

- **状态：** `beta`
- **描述：** SHA-256 派生的确定性 `[0,1)` 伪随机

### markdown

`Utils.markdown` 绑定 `MarkdownMgr`：MD 模版 ``{{:token}}`` 填充。

| 方法 | 说明 |
|------|------|
| `load_template(path)` | 从文件加载模版，扫描 token |
| `from_text(text)` | 从字符串加载模版 |
| `fill(token, content)` / `fill_many({...})` | 填值（同名后写覆盖；非 str → `""`） |
| `save(path)` / `render()` | 未填 token 报错；写出 MD |
| `clear()` | 清空已填值 |

- **状态：** `beta`
- **举例：**

```python
from core.infra.utils import Utils

mgr = Utils.markdown.load_template("REPORT_TEMPLATE.md")
mgr.fill("wall_clock_seconds", "3s")
mgr.save("out/REPORT.md")
```

---

## contracts

| 符号 | 说明 |
|------|------|
| `PERIOD_DAY` … `PERIOD_YEAR` | 周期类型字符串常量 |
| `PeriodType` / `ArchiveFormat` | Literal 别名 |
