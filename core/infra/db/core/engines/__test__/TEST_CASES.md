# 测试用例 — `infra.db` / `core/engines`

**覆盖版本：** `0.5.0`  
**本文件位置：** `core/engines/__test__/`

## Scope

Engine 挂载骨架与跨 backend settings / meta。

## 边界

**负责：** factory、ABC、`EngineConfigMeta` / backend settings  
**不负责：** 单 backend 深度行为（见 `engines/<backend>/__test__`）

| Case 文件 | 说明 |
|-----------|------|
| `test_engines_skeleton.py` | 挂载骨架 |
| `test_engine_settings.py` | settings + build_engine_meta |
