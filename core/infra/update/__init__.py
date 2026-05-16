"""升级相关扩展（与 ``core/infra/db`` 并列）。

- ``post_upgrade/``：主流程结束后的收尾动作（updater 步骤 11 子进程调用）
- ``update/db/``：数据库迁移用单步数据脚本（由 ``infra.db`` 迁移执行器调用）
"""
