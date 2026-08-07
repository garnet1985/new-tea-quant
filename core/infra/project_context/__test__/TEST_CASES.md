# 测试用例 — `infra.project_context`

**模块：** `infra.project_context`  
**覆盖版本：** `0.5.0`

## Scope

验证门面 `ProjectContext` 与 path / config / meta / cache / discovery / types 公开契约（对齐 `API.md`）。

## 边界

**负责：** 公开 namespace API；contracts 异常与常量  
**不负责：** 业务配置语义（市场规则等由上层模块负责）；内部 Manager 行为（见 `core/__test__/`）

| 文件 | 说明 |
|------|------|
| `test_api.py` | 公开 API 契约 smoke（`force_run`） |

内部 Manager 行为测试见 `core/__test__/`（`test_path_manager.py`、`test_config_manager.py`、`test_discovery_manager.py`、`test_project_context_manager.py`）。
