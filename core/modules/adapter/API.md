# Adapter API 文档

**版本：** `0.3.0`  
**最低支持核心版本：** `>=0.4.0`

> 须与 `module_info.yaml` 一致。公开入口状态最高 **`beta`**。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。

**公开约定：** 包根仅导出 `Adapter`；基类与 `HistoryLoader` 从 [`contracts.py`](./contracts.py) 导入。实现位于 `core/`，禁止 deep-import。

---

## Adapter

**描述：** Scanner 后续处理适配器门面（静态 API）

#### validate

`Adapter.validate(adapter_name: str) -> tuple[bool, str]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.3.0`
- **描述：** 校验 `userspace.extensions.adapters.<name>.adapter` 可加载且含合法 `BaseOpportunityAdapter` 子类
- **返回值：** `(ok, error_message)`；成功时 message 为空串

#### load_class

`Adapter.load_class(adapter_name: str) -> type | None`

- **类型：** `static`
- **状态：** `beta`
- **描述：** 按名加载 adapter 类；失败返回 ``None``（跨模块入口；勿 deep-import ``AdapterLoader``）

---

## contracts

| 符号 | 说明 |
|------|------|
| `BaseOpportunityAdapter` | userspace adapter 基类（须实现 `process`） |
| `HistoryLoader` | 读取 price_factor 历史模拟统计 |
