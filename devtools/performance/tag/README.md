# Tag 性能基准测试

目标：
  - 定义 Tag 系统的性能基线（entity_timeline 和 calendar_sliced 两种模式）
  - 测试不同配置下的表现
  - 与 Strategy 性能测试对比

用法：
    # 运行 entity_timeline 模式基准测试
    python scripts/run_tag_timeline_benchmark.py

    # 运行 calendar_sliced 模式基准测试
    python scripts/run_tag_sliced_benchmark.py

    # 使用自定义股票池大小
    python scripts/run_tag_timeline_benchmark.py --stock-limit 1000

输出：
  results/
  ├── timeline/
  │   └── baseline.json          # entity_timeline 基准结果
  └── sliced/
      └── baseline.json          # calendar_sliced 基准结果

目录结构：

```
devtools/performance/tag/
├── README.md                              # 本文档
├── test_base_tags/                        # 基准 Tag 场景（每次测试自动复制到 userspace）
│   ├── entity_timeline/                   # Entity Timeline 模式基准场景
│   │   ├── settings.py                    # 场景配置（轻量级市值分档）
│   │   └── tag_worker.py                  # 计算逻辑
│   └── calendar_sliced/                   # Calendar Sliced 模式基准场景
│       ├── settings.py                    # 场景配置（横截面百分位）
│       └── tag_worker.py                  # 计算逻辑
└── scripts/
    ├── run_tag_timeline_benchmark.py      # Entity Timeline 模式测试脚本
    ├── run_tag_sliced_benchmark.py        # Calendar Sliced 模式测试脚本
    └── results/                           # 测试结果输出
        ├── timeline/
        └── sliced/
```

Base Tag 场景说明：

1. **entity_timeline** (bench_cap_tier):
   - 用途: 测试逐实体标签计算的吞吐量
   - 逻辑: 简化的市值分档 (micro/low/mid/high)
   - 特点: 轻量级、状态变化检测、每个实体独立处理
   - 代表: 典型的时间序列打标场景

2. **calendar_sliced** (bench_cap_pct):
   - 用途: 测试时间切片批量处理的 IO 和计算性能
   - 逻辑: 市值百分位排名 (0-100)
   - 特点: 横截面计算、需要全市场数据、每日输出
   - 代表: 因子预处理中的横截面标准化步骤

工作流程：

```
[测试开始]
    ↓
从 test_base_tags/<mode> 复制到 userspace/extensions/tags/bench_tag_<mode>
    ↓
清缓存 → 运行 CLI → 收集 performance_report.json → 提取指标
    ↓
生成 baseline.json + analysis.md
    ↓
删除临时 bench_tag_<mode> 目录
    ↓
[测试完成]
```

日期: 2026-06-22
作者: AI Assistant (基于 Strategy 性能测试框架)
