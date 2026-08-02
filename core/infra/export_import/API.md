# Export / Import API 文档

**版本：** `0.3.0`  
**最低支持核心版本：** `>=0.4.0`

> 须与 `module_info.yaml` 一致。  
> 本文档是本模块公开调用面的**唯一人读 API 文档**。  
> core 仍为 `0.x`：公开入口状态最高 **`beta`**（禁止 `stable`）。  
> 所列门面入口须有 `__test__/test_api.py` 覆盖。

快速开始见 [QUICKSTART.md](./QUICKSTART.md)。术语见 [glossary.yaml](./glossary.yaml)。架构见 [ARCHITECTURE.md](./docs/ARCHITECTURE.md)。

**公开约定：** 包根仅导出 `ExportImport`；类型从 [`contracts.py`](./contracts.py) 导入，或经 `ExportImport.types`。

---

## ExportImport

**描述：** 制品打包 / 安装门面类（Facade）— `archive` / `install` / `types` 命名空间

### archive

#### create

`ExportImport.archive.create(specs, *, metadata=None, output_path=None) -> tuple[BundleManifest, bytes | Path]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 按 `ArtifactSpec` 列表收集文件并打 zip；`output_path` 缺省则返回 bytes
- **举例：**

```python
from pathlib import Path
from core.infra.export_import import ExportImport

ArtifactSpec = ExportImport.types.ArtifactSpec
manifest, blob = ExportImport.archive.create(
    [
        ArtifactSpec(
            kind="strategy",
            name="demo",
            source_dir=Path("userspace/strategies/demo"),
            archive_prefix="strategies/demo",
            target_relative="strategies/demo",
        )
    ],
    metadata={"bundle_type": "strategy"},
)
```

#### extract

`ExportImport.archive.extract(source, *, dest_dir=None) -> tuple[Path, BundleManifest]`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 解压 zip（Path 或 bytes）到目录，返回根路径与 manifest

---

### install

#### preflight

`ExportImport.install.preflight(extracted_root_or_manifest, userspace_root, policy) -> PreflightResult`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 安装前冲突预检（可传已解压根目录或 `BundleManifest`）

#### install

`ExportImport.install.install(archive, userspace_root, policy) -> InstallResult`

- **类型：** `static`
- **状态：** `beta`
- **引入版本：** `0.2.0`
- **描述：** 解压并按冲突策略落盘到 userspace

---

### types

**描述：** 与 `contracts` 同源的类型挂载点（`ArtifactSpec`、`ConflictPolicy`、`BundleManifest`、`PreflightResult`、`InstallResult` 等）

---

## contracts（`core.infra.export_import.contracts`）

| 符号 | 说明 | 状态 |
|------|------|------|
| `ConflictPolicy` | reject / skip_existing / overwrite | `beta` |
| `ArtifactSpec` | 单个制品规格 | `beta` |
| `BundleManifest` / `ManifestEntry` | 清单 | `beta` |
| `PreflightResult` / `ConflictItem` | 预检 | `beta` |
| `InstallResult` | 安装结果 | `beta` |
| `CollectedFile` | 归档内文件条目（偏内部） | `beta` |
