"""
Userspace data contract extension.

扩展入口（当前核心命名）：
- 在 `mapping.py` 中提供 userspace 映射：`data_id -> spec`（shape/meta + loader key）
- 在 `loaders/` 目录中实现对应 loader（需继承 `BaseLoader`）

该包由 core discovery 自动扫描并合并。
"""
