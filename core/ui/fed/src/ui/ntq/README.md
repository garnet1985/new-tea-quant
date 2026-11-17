# `ui/ntq` — NTQ 特有公用组件

应用壳与产品向固定模板（导航、面包屑、页头 Banner、报告区块、Python dict 编辑器等）。

与 `input` / `layout` 等**通用原语**分开：这里可以绑产品壳约定（Router、顶栏高度），但**路由表 / 站点 URL / 业务映射**仍由应用层传入，不写死在组件里。

| 组件 | 状态 | 说明 |
|------|------|------|
| `appBrand` | ready | 顶栏品牌标 |
| `appNav` | ready | 顶栏导航壳（`items` 驱动） |
| `appBreadcrumbs` | ready | 面包屑（`items` + `current`） |
| `pageBanner` | ready | 页头标题条 |
| `reportBlock` | ready | 回测/报告小节固定壳（对齐旧 `views/sectionBlock`） |
| `pythonDictEditor` | ready | JSON / Python dict 调试面板 |

产品页迁移前仍可读 `views/`；新代码优先 `ui/ntq/*`。报告小节统一用 `reportBlock`，不要各页自造边框壳。
