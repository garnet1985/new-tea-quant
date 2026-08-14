"""仅 per_entity（entity_based ↔ slice_based）共用的 BE 编排件。

- job_payload: BacktestEngine job 核心 payload
- pipeline_hooks: 可 pickle 的主进程 RunCallbacks 分派

模块级共用（settings / hooks / flush 等）见 ``engines/shared``。
"""
