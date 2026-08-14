# <Module Display Name> — 快速开始

<!--
  可选：给「需要马上跑起来」的人。不需要则删除本文件，并去掉 README 中的链接。
-->

**模块：** `<namespace.module_name>` · **版本：** `<module.version>`

`<一两句：本快速开始覆盖哪条主路径。>`

---

## 前置条件

- `<环境 / 依赖 / 配置；无则写「无特殊前置」>`
- 公开契约见 [API.md](./API.md)

---

## 最小示例

```python
from <package> import <Facade>
from <package>.contracts import <Types>

<最短可运行代码；与当前实现一致；占位用注释标明>
```

**预期结果：** `<成功时看到什么>`

---

## 下一步

- [API.md](./API.md)
- [glossary.yaml](./glossary.yaml)
- [docs/CONCEPTS.md](./docs/CONCEPTS.md)<!-- 若无则删 -->
- [README.md](./README.md)

```bash
python3 -m pytest <module_path>/__test__/ -q
```
