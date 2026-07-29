# Tag 性能基准（已退役）

旧基准脚本依赖已删除的 `BaseTagWorker` / `engines.sliced` / 模块内 CLI，**已移除**。

当前可用：

- userspace 场景：`userspace/extensions/tags/bench_test`、`bench_bottleneck_test`（`TagHooks`）
- 运行：`cli.py tag --scenario bench_test`（或对应路径）
- 调度调参：`core/default_config/worker.json` → `job_pipeline.tag`

若要重建正式 benchmark，按新 `Tag` + entity/slice pipeline 重写后再放回本目录。
