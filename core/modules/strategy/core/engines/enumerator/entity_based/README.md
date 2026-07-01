# entity_based 流程
#
# resolver/jobs.py     → 构建每股 job
# pipeline.py          → BacktestEngine.entity_based 调度
# worker.py            → 子进程入口（薄包装）
# compute.py           → timeline 扫描核心计算
# context/data.py      → DataContext 组装
# context/runtime.py   → 模式 runtime 视图
# context/status.py    → 运行状态
