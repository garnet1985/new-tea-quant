# MIGRATED

本目录下的 `tag_worker.py` / 分析脚本依赖已删除的旧
`core.modules.tag.engines.*`（`BaseTagWorker` / sliced runtime）。

新路径：`TagHooks` + `core.modules.tag.core` entity/slice pipelines。
AUDIT: 待按新 hooks 重写 benchmark，或删除本目录。
