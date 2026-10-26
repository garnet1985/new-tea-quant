# Utils 详细设计

**版本：** `0.2.2`

> 本节决定已独立到 [DECISIONS.md](./DECISIONS.md)（自动编号 DEC-XX）## 实现备注

- `date` 内部拆 `parser` / `calculator` / `period` / `constants`；解析与季度辅助以 `parser` 为单一来源
- `types` 的 pandas 依赖仅在 DataFrame 方法内 import
- `math.deterministic_unit_float`：SHA-256 → `[0,1)`，可复现
- `locale.is_china`：认大陆 IANA 地名（`Asia/Shanghai` 等）或 `zh_CN`，**不用** UTC+8；不含网络探测
- `pkg`：pip / npm 依赖源。`USE_CHINA_MIRROR` → `is_china` → pypi 探活。国内默认中科大（可换源）+ npmmirror
- 无界查询下界 `get_query_date_range_min` 仍读配置；业务「默认开始日」请用 `ProjectContext.config`

## 相关文档

- [ARCHITECTURE.md](./ARCHITECTURE.md)
