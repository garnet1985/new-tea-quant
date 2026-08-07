# 测试用例 — `infra.db` / `core/engines`

**覆盖版本：** `0.5.0`  
**本文件位置：** `core/engines/__test__/`

## Scope

Engine **挂载骨架**（factory / ABC）跨 backend 行为。  
settings / meta 解析细节有 UT 即可，不在本文逐条展开。

## 边界

**负责：** factory 挂载、ABC 契约  
**不负责：** 单 backend 深度行为（见 `engines/<backend>/__test__`）

## Scenario：engine_mount

| Case 文件 | 说明 |
|-----------|------|
| `test_engines_skeleton.py` | 按 engine_key 挂载 mysql / postgresql / duckdb |
