# `ui/ntq` — NTQ 特有公用组件

应用壳与业务向复合组件（导航、页头 Banner、Python dict 编辑器等）。

与 `input` / `layout` 等**通用原语**分开：这里可以绑产品约定（路由、校验流程、品牌壳），不要求别处可直接复用。

| 组件 | 状态 | 说明 |
|------|------|------|
| `appNav` | stub | 顶栏导航，迁自 `views/appNav` |
| `pageBanner` | stub | 页头标题条，迁自 `views/pageBanner` |
| `pythonDictEditor` | ready | JSON / Python dict 调试面板 |

产品页迁移前仍可读 `views/`；新代码优先 `ui/ntq/*`。
