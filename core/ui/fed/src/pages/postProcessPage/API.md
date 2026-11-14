# 后续处理控制台 API

FED `/advanced/post-process` 页面对应的 BFF 契约。实现见 `core/bff/APIs/post_process/`。

## HTTP 前缀

- 蓝图前缀 `/api`；下文路径完整为 `/api/v1/post-process/...`。

## 模型说明

- **Adapter（执行单元）**：`userspace/extensions/post_process/adapters/<name>/`
- **PostProcessor（处理方案）**：`userspace/extensions/post_process/post_processors/<key>/`
- **启用模型**：全局多活；每个策略扫描 `present` 后跑全部 `is_enabled: true` 的方案
- **步骤顺序**：由各 adapter 的 `depends_on` 拓扑计算，不是拖拽线性 pipeline

## API 清单

| 方法 | 路径 | 用途 |
|------|------|------|
| GET | `/v1/post-process/adapters` | Adapter 目录 |
| GET | `/v1/post-process/processors` | 方案列表（含步骤、拓扑序、校验、dry_run 汇总） |
| POST | `/v1/post-process/processors/<key>/enabled` | body `{ enabled: bool }` |
| PUT | `/v1/post-process/processors/<key>/adapters` | body `{ adapters: { name: { depends_on: [] } } }` |

## 响应信封

成功：`{ "status": "ok", "message": { ... } }`  
失败：`{ "status": "error", "message": { "detail": "..." } }`

### GET adapters — message

```json
{
  "items": [
    {
      "name": "presenter",
      "display_name": "终端展示",
      "validate": { "ok": true, "message": "" },
      "supports_dry_run": false,
      "default_dry_run": null
    }
  ],
  "total": 1
}
```

### GET processors — message

```json
{
  "items": [
    {
      "key": "presenter",
      "name": "Presenter",
      "is_enabled": true,
      "on_error": "continue",
      "on_empty": "run",
      "adapters": [
        {
          "name": "presenter",
          "display_name": "终端展示",
          "depends_on": [],
          "status": "live",
          "validate": { "ok": true, "message": "" }
        }
      ],
      "execution_order": ["presenter"],
      "order_error": "",
      "validate": { "ok": true, "message": "" }
    }
  ],
  "total": 1
}
```

步骤 / 执行单元 `status` 优先级：`unavailable`（红）> `dry_run`（黄）> `live`（绿）。  
另有 `remark`：红=缺少配置原因，黄=`当前是测试模式`，绿=`可以正常使用`。

### POST enabled / PUT adapters — message

```json
{ "item": { "...": "同 processors 单项" } }
```

PUT 时若 UI 未传 `config`，服务端保留原 YAML 中该 adapter 的 `config`。
