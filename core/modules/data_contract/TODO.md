# Data Contract — 待办（0.5.0 改造）

**0.5.0 Facade / 黑盒 cache / 下游迁移 / 文档：** ✅ 已完成。

---

## 未来：PER_ENTITY DataFrame + Parquet 缓存

**状态：** 未做  
**优先级：** 低

详见 [`docs/ROADMAP.md`](docs/ROADMAP.md) 阶段 6 与本文件原验收项（Parquet 命中、Facade 对 DataFrame 等价行为）。

---

## 测试

- [x] `__test__/test_cases.yaml` 用例注册表
- [x] `__test__/README.md` 测试说明

运行：`python3 -m pytest core/modules/data_contract/__test__/ -q`（当前 21 passed）
