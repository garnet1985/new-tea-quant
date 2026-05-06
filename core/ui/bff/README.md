# BFF API

`core/ui/bff` 是 FED 的 Python BFF 层（Flask）。

## 启动

在仓库根目录执行：

```bash
python -m core.ui.bff.app
```

默认配置读取：

- `core/ui/bff/conf.py`
  - `HOST`
  - `PORT`
  - `DEBUG`
  - `CORS_*`

## 说明

- 应用入口与注册：`core/ui/bff/app.py`
- API 按业务拆分：`core/ui/bff/APIs/`
- 每个业务建议目录化：
  - `routes.py`：endpoint 与请求解析
  - `service.py`：业务逻辑
  - `runtime.py` / `helpers.py`：共享状态、流程或工具
- 跨业务复用能力：`core/ui/bff/shared/`
  - 仅放跨业务通用方法（如 response/file ops）
