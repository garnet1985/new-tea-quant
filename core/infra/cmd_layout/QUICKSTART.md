# 命令行布局 — 快速开始

**模块：** `infra.cmd_layout` · **版本：** `0.1.2`

最短路径：用门面类 `CmdLayout` 生成可打印字符串。

---

## 前置条件

- 无特殊前置
- 公开契约见 [API.md](./API.md)

---

## 最小示例

```python
from core.infra.cmd_layout import CmdLayout

print(CmdLayout.title.banner("枚举报告"))
print(CmdLayout.title.section("汇总"))
print(CmdLayout.separator.line(width=40))
print(CmdLayout.bar_chart.render([("win", 42), ("loss", 18)], title="胜负"))
print(CmdLayout.icon.get("success"))
```

**预期结果：** 终端打印 ASCII 标题块、小节、分割线、条形图，以及成功图标（UTF-8 下为 emoji，部分 Windows 终端为 `[OK]`）。

---

## 下一步

- [API.md](./API.md)
- [glossary.yaml](./glossary.yaml)
- [README.md](./README.md)

```bash
python3 -m pytest core/infra/cmd_layout -q
```
