"""
Backtest Scheduler模块 - 回测调度和编排

核心功能：
- 回测业务调度（时间线/切片模式）
- 任务编排和队列管理（QUEUE/BATCH策略）
- Dispatch规划（entities_per_job、max_workers）
- 与MQ的抽象接口（方便未来迁移）

定位：
- 业务调度层（不属于infra）
- 理解回测语义
- 指挥执行器工作

使用模块：
- modules.tag（Tag回测）
- modules.strategy（Strategy回测）
"""

__version__ = "0.1.0"
__author__ = "New Tea Quant Team"
__description__ = "回测调度模块 - 业务调度层，tag/strategy共用"