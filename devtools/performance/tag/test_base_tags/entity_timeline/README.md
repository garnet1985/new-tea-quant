# Entity Timeline 模式基准 Tag 场景

用途：
  - 性能测试的标准 baseline（entity_timeline 模式）
  - 验证逐实体标签计算的吞吐量和稳定性

特点：
  - 轻量级计算（仅读取 indicators + 简单分类）
  - 代表典型的时间序列打标场景
  - 每个实体独立处理，无跨实体依赖

与 Sliced 模式对比：
  - Timeline: 逐实体遍历（适合事件驱动、状态变化检测）
  - Sliced: 时间切片批量（适合横截面排名、全市场统计）
