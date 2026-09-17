# 测试用例 — `modules.assistant.core`

**模块：** `modules.assistant`  
**版本：** `0.1.0`  
**本文件位置：** `core/__test__/`

---

## Scope

验证供应商扫描在隔离目录下的行为（经 monkeypatch 的 `ProjectContext.path`）。`AssistantManager` 为编排薄壳，发现语义以 `ProviderCatalog` 为准。

## 边界

**负责**

- 合法 config 被发现
- 缺字段 / 无目录 / 禁用项 / 密钥探测
- 不硬编码 userspace 绝对路径

**不负责**

- 门面导出（见模块根 `__test__/test_api.py`）

**允许的测试类型（本目录）：** `unit`

---

## Scenario：catalog

| Case（pytest 函数名） | 文件 | 说明 |
|----------------------|------|------|
| `test_empty_when_root_missing` | `test_provider_catalog.py` | 目录不存在返回空列表 |
| `test_discovers_valid_provider` | `test_provider_catalog.py` | 读 base_url / model / has_api_key |
| `test_skips_incomplete_config` | `test_provider_catalog.py` | 缺 model 的目录被跳过 |
| `test_keeps_disabled_provider` | `test_provider_catalog.py` | `enabled=False` 仍列出 |
| `test_paths_come_from_project_context` | `test_provider_catalog.py` | 真实 Path API 落在 extensions/assistant |
