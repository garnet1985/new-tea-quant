# 标签场景（`userspace/tags/`）

每个子目录通常是一个**标签场景**：`settings.py` + `tag_worker.py`（继承 `BaseTagWorker`）。
**请注意：目前的tag系统必须是时序数据才能使用，之后会扩展到更泛的使用场景**


## 为什么这里有两类示例

Tag 配置现在明确分成两种 `tag_target_type`：

- `entity_based`：标签属于具体实体（如每只股票）。
- `general`：标签属于全局/上下文（如宏观环境）。

之所以要分这两类，是为了把“标签归属对象”语义说清楚，避免把实体标签和全局标签混在同一个配置心智里。


## 这几个示例分别在演示什么

- `example/`
  - **类型**：`entity_based`
  - **用途**：最小可运行示例，展示标准配置结构与基础 worker 写法。
- `momentum/`
  - **类型**：`entity_based`
  - **用途**：更贴近真实因子计算的例子（历史窗口、按月/增量逻辑等）。
- `macro_regime/`
  - **类型**：`general`
  - **用途**：演示不依赖单实体 owner 的全局标签场景，以及 `data.tag_time_axis_based_on` 的必填用法。


## 怎么用

1. 新手先从 `example/` 开始，确认链路跑通。  
2. 需要全局标签时，参考 `macro_regime/` 的 `general` 配置。  
3. 需要更复杂实体标签时，再参考 `momentum/`。  
4. 跑标签计算：`python start-cli.py -t`；指定场景：`python start-cli.py -t --scenario <场景名>`（与目录/配置中的场景名一致）。  

详细设计见 [标签系统用户指南](../../docs/user-guide/tag-system.md) 与 [core/modules/tag/README.md](../../core/modules/tag/README.md)。
