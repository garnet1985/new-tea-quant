# 标签场景（`userspace/tags/`）

每个子目录通常是一个**标签场景**：`settings.py` + `tag_worker.py`（继承 `BaseTagWorker`）。

## 怎么用

1. 参考 `example/` 或根下的 `example_settings.py` 了解配置形状。  
2. 跑标签计算：`python start-cli.py -t`；指定场景：`python start-cli.py -t --scenario <场景名>`（与目录/配置中的场景名一致）。  

详细设计见 [标签系统用户指南](../../docs/user-guide/tag-system.md) 与 [core/modules/tag/README.md](../../core/modules/tag/README.md)。
