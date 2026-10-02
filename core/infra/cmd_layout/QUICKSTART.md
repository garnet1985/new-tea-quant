# 命令行布局 — 快速开始

**模块：** `infra.cmd_layout` · **版本：** `0.2.0`

最短路径：用门面类 `CmdLayout` 生成可打印字符串。

---

## 前置条件

- 无特殊前置
- 公开契约见 [API.md](./API.md)

---

## 最小示例

```python
from core.infra.cmd_layout import CmdLayout, i

CmdLayout.title.print_h1(f"{i('chart')} 归因对照")
CmdLayout.title.print_h2("参数贡献度")
CmdLayout.title.print_h3("有 / 无")
CmdLayout.title.print_h4("PE分位上限")
print(CmdLayout.text.meta(["组 3", "对照上 4 套"]))
print(CmdLayout.text.indent("关 PE 后账户少 12 个点。"))
CmdLayout.table.print(
    ["旋钮", "收益"],
    [["止损", "12%"], ["PE", "3%"]],
)
print(CmdLayout.bar_chart.render([("win", 42), ("loss", 18)], title="胜负"))
```

**预期结果：** 终端打印 h1 星号框、h2 下划线、h3 三连 `-`、h4 `###`、meta/缩进正文、对照表与条形图。

兼容旧路径：`CmdLayout.title.banner` / `section` 仍可用。

---

## 下一步

- [API.md](./API.md)
- [glossary.yaml](./glossary.yaml)
- [README.md](./README.md)

```bash
python3 -m pytest core/infra/cmd_layout -q
```
