# Database 模块测试

**架构版本：** `0.5.0`

- **模块根 `__test__/`**：`test_api.py`（必须）+ 可选 `test_integration_*.py`
- **功能包 `__test__/`**：实现单测，见 `core/**/__test__/`
- updater 迁移子进程测试在 `setup/updater/__test__/`（不属于本模块）

## 运行

```bash
# 公开契约
pytest core/infra/db/__test__/test_api.py -v

# 模块根（含 integration）
pytest core/infra/db/__test__/ -v

# 全量（含包内下沉单测）
pytest core/infra/db/ -v -k test_
```

refactor freeze 下多数包内用例需 `pytest.mark.force_run`。

## 相关文档

- [TEST_CASES.md](./TEST_CASES.md)
- [../API.md](../API.md)
- [../docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md)
