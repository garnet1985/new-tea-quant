# ntqIcon

> 路径 `ui/icon/ntqIcon`（标准原语；`views/` 暂只读，迁移另做）

```js
import NtqIcon, { NTQ_ICON_NAMES } from 'ui/icon/ntqIcon';

<NtqIcon name="add" size="md" />
<NtqIcon name="success" size="lg" tone="success" />
```

## 参数

| 参数 | 取值 | 默认 |
|------|------|------|
| `name` | 详见下方列表 | 必填 |
| `size` | `sm` `md` `lg` `xl` `xxl` | `md` |
| `tone` | `''` `muted` `success` `error` `warning` `disabled` `cyan` `violet` | `''` |
| `spin` | boolean | `false` |

## 全部 name

`add` · `arrowBack` · `assistantCat` · `calendar` · `cancel` · `chat` · `chevronRight` · `dataObject` · `delete` · `download` · `expandMore` · `folderOpen` · `help` · `history` · `info` · `monitoring` · `pin` · `pinFilled` · `play` · `playCircle` · `radioUnchecked` · `refresh` · `remove` · `search` · `sentimentDissatisfied` · `sentimentSatisfied` · `settings` · `success` · `syncAlt` · `tactic` · `trash` · `uploadFile` · `warning` · `webhook`

运行时列表：`NTQ_ICON_NAMES`（与 `NTQ_ICON_MAP` 的 key 一致）。

> `expandMore` / `chevronRight` 共用箭头 SVG；`expandMore` 额外旋转。
