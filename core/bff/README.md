# BFF API

`core/bff` 是 FED 的 Python BFF 层（Flask）：HTTP 编排 + 调用 `core.modules` Facade，
页面侧数据重组放在 `support/`（原各模块 `bff_support`）。

## 启动

在仓库根目录执行：

```bash
python -m core.bff.app
```

默认配置读取：

- `core/bff/conf.py`
  - `HOST`
  - `PORT`
  - `DEBUG`
  - `CORS_*`

## 说明

- 应用入口与注册：`core/bff/app.py`
- API 按业务拆分：`core/bff/APIs/`
  - `routes.py`：endpoint 与请求解析
  - `*_stack.py` / `service.py`：懒加载编排
- 页面适配：`core/bff/support/`（strategy / tag …）
- 跨业务复用：`core/bff/shared/`（response / file_ops）
- 生产模式托管 FED build：`static_ui.py` → `core/ui/fed/build`
