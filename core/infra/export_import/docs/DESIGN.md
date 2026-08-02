# Export / Import 详细设计

**版本：** `0.3.0`

实现向细节；公开入口见根目录 [API.md](../API.md)。

## 数据流

```text
ArtifactSpec[] → collect → zip + BundleManifest
archive bytes/Path → extract → (root, Manifest)
Manifest + userspace + ConflictPolicy → preflight → PreflightResult
archive + userspace + policy → install → InstallResult（落盘）
```

## 冲突策略

| Policy | 行为 |
|--------|------|
| `reject` | 存在冲突则预检失败，不安装 |
| `skip_existing` | 跳过已存在目标 |
| `overwrite` | 覆盖已存在目标 |

## 运行时排除

收集时跳过 `results/`、`cache/`、`__pycache__` 等（见 `core/runtime_excludes.py`）。
