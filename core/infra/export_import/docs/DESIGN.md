# Export / Import 详细设计

**版本：** `0.3.0`

实现向细节；公开入口见根目录 [API.md](../API.md)。

## 组件（实现类）

| 类 | 职责 |
|----|------|
| `BundleArchive` | zip 打包 / 解压（**仅** stdlib `zipfile`） |
| `ArtifactCollector` | 按 `ArtifactSpec` 收集文件 |
| `BundleManifestIO` | manifest.json 读写与校验 |
| `ConflictChecker` | 安装前冲突预检 |
| `BundleInstaller` | 落盘安装 |
| `RuntimeExcludes` | 收集时跳过规则 |

## 数据流

```text
ArtifactSpec[] → ArtifactCollector → BundleArchive.create → zip + BundleManifest
archive bytes/Path → BundleArchive.extract → (root, Manifest)
Manifest + userspace + ConflictPolicy → ConflictChecker.preflight → PreflightResult
archive + userspace + policy → BundleInstaller.install_archive → InstallResult
```

## 冲突策略

| Policy | 行为 |
|--------|------|
| `reject` | 存在冲突则预检失败，不安装 |
| `skip_existing` | 跳过已存在目标 |
| `overwrite` | 覆盖已存在目标 |

## 运行时排除

收集时跳过 `RuntimeExcludes` 中的目录名 / 后缀（`results/`、`cache/`、`__pycache__` 等）；**无**按 strategies/tags 路径再写特殊分支。

## 设计决策

### D1：stdlib zip 为唯一实现

去掉系统 `zip` 双路径，保证跨平台行为一致；目录条目由实现显式写入。

### D2：实现一律类方法，门面薄委托

公开只经 `ExportImport.*`；不导出模块级自由函数。
