# Project Context 单元测试

用例清单见 [TEST_CASES.md](./TEST_CASES.md)。

```bash
# 公开 API 契约
python3 -m pytest core/infra/project_context/__test__/test_api.py -q

# 全模块（含 core/__test__ 内部行为测试）
NTQ_TESTS_ENABLED=1 python3 -m pytest core/infra/project_context -q
```

- **`__test__/`** — 公开 Facade / contracts 契约（`test_api.py`）
- **`core/__test__/`** — PathManager、ConfigManager、DiscoveryManager 等内部行为
