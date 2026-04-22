# BFF API

`core/ui/bff` 是 FED 的 Python BFF 层（Flask）。

## 启动

在仓库根目录执行：

```bash
python -m core.ui.bff.app
```

可通过环境变量覆盖默认监听：

- `NTQ_BFF_HOST`（默认 `127.0.0.1`）
- `NTQ_BFF_PORT`（默认 `5001`）
- `NTQ_BFF_DEBUG`（默认 `false`）

## 说明

- 统一入口：`core/ui/bff/api.py`
- 路由定义：`core/ui/bff/routes.py`
- 业务 API：`core/ui/bff/APIs/`
