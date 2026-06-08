# Export / Import（`infra.export_import`）

Userspace 制品**打包与安装**的公用基础设施，与具体业务（策略包、数据包等）解耦。

## 职责

- 从目录收集可导出文件（跳过 `results/`、`cache/`、`__pycache__` 等运行时路径）
- 生成 `manifest.json` + zip 归档
- 解压、安装前冲突预检（`reject` / `skip_existing` / `overwrite`）
- 原子写入目标路径

## 不负责

- 从 strategy settings 解析 tag / adapter 依赖（由 `modules.strategy` 编排层完成）
- 导入后的 discovery / validate（由调用方完成）

## 快速示例

```python
from pathlib import Path

from core.infra.export_import import (
    ArtifactSpec,
    ConflictPolicy,
    create_bundle_archive,
    install_bundle_archive,
    preflight_install,
)

spec = ArtifactSpec(
    kind="strategy",
    name="demo",
    source_dir=Path("userspace/strategies/demo"),
    archive_prefix="strategies/demo",
    target_relative="strategies/demo",
)

manifest, blob = create_bundle_archive([spec], metadata={"bundle_type": "strategy"})

preview = preflight_install(manifest, Path("userspace"), ConflictPolicy.REJECT)
result = install_bundle_archive(blob, Path("userspace"), ConflictPolicy.SKIP_EXISTING)
```

## 测试

```bash
python3 -m pytest core/infra/export_import/__test__/ -q
```
