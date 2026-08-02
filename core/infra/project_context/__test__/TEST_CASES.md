# 测试用例 — `infra.project_context`

**模块：** `infra.project_context`  
**覆盖版本：** `0.5.0`

## Scope

验证门面 `ProjectContext` 与 path / config / meta / cache / discovery 行为（对齐 `API.md`）。

## 边界

**负责：** 公开 namespace API；contracts 异常与常量  
**不负责：** 业务配置语义（市场规则等由上层模块负责）

| 文件 | 说明 |
|------|------|
| `test_api.py` | 公开 API 契约（`force_run`） |
| `test_path_manager.py` | PathManager 内部路径 |
| `test_config_manager.py` | ConfigManager 合并 |
| `test_discovery_manager.py` | 配置发现与 overridable 加载 |
| `test_file_manager.py` | FileManager 原语 |
| `test_project_context_manager.py` | Facade 行为补充 |
