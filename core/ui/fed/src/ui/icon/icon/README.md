# icon

> 路径 `ui/icon/icon`。CSS 根类暂仍为 `.ntq-icon`。

```js
import Icon, { ICON_NAMES } from 'ui/icon/icon';
// 或：import { Icon } from 'ui';

<Icon name="add" size="md" />
<Icon name="success" size="lg" tone="success" />
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

运行时列表：`ICON_NAMES`（与 `ICON_MAP` 的 key 一致；旧名 `NTQ_ICON_*` 仍可作别名）。
