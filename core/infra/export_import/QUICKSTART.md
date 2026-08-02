# Export / Import — 快速开始

**模块：** `infra.export_import` · **版本：** `0.3.0`

最短路径：打一个制品包并预检安装。

---

## 最小示例

```python
from pathlib import Path
from core.infra.export_import import ExportImport

ArtifactSpec = ExportImport.types.ArtifactSpec
ConflictPolicy = ExportImport.types.ConflictPolicy

spec = ArtifactSpec(
    kind="strategy",
    name="demo",
    source_dir=Path("userspace/strategies/demo"),
    archive_prefix="strategies/demo",
    target_relative="strategies/demo",
)
manifest, blob = ExportImport.archive.create([spec])
preview = ExportImport.install.preflight(manifest, Path("userspace"), ConflictPolicy.REJECT)
print(preview.ok, len(preview.conflicts))
```

**预期结果：** 得到 `BundleManifest` 与 zip bytes；预检返回冲突列表。

---

## 下一步

- [API.md](./API.md)

```bash
python3 -m pytest core/infra/export_import/__test__/test_api.py -q
```
