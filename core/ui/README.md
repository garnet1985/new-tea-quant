# UI 模块（`core/ui`）

`core/ui` 是 NTQ 的 UI 子系统，包含：

- `fed/`：前端（React）
- `bff/`：后端 BFF（Flask），为 FED 提供业务 API，并编排对 `core/modules/*` 的调用
- `docs/`：UI 侧设计与接口约定文档
- `module_info.yaml`：UI 模块元信息与依赖声明

## 如何启动

推荐使用仓库根目录的 `launcher.py` 一键启动与安装引导（见根目录 `README.md`）。

如需单独启动 BFF（在仓库根目录）：

```bash
python -m core.ui.bff.app
```

FED 的开发/构建方式见 `core/ui/fed/package.json`。

## 文档入口

- BFF 说明：`core/ui/bff/README.md`
- UI 设计草案与约定：`core/ui/docs/`

