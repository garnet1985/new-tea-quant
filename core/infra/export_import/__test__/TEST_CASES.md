# 测试用例 — `infra.export_import`

**模块：** `infra.export_import`  
**覆盖版本：** `0.3.0`

## Scope

验证门面 `ExportImport` 与打包 / 安装行为（对齐 `API.md`）。

## 边界

**负责：** archive / install namespace；contracts 类型经 `ExportImport.types`  
**不负责：** strategy 业务编排

| 文件 | 说明 |
|------|------|
| `test_api.py` | 公开 API 契约 |
| `test_export_import.py` | 打包 / 安装行为 |
