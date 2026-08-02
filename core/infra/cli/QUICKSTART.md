# CLI — 快速开始

**模块：** `infra.cli` · **版本：** `0.4.2`

最短路径：仓库根启动用户 / 开发入口，或在入口脚本里调用门面类 `Cli`（见 [glossary.yaml](./glossary.yaml) 的 Facade / Cli）。

---

## 前置条件

- 在仓库根目录执行（或等价保证 `cli.py` / `devcli.py` 可找到项目根）
- 公开契约见 [API.md](./API.md)

---

## 最小示例

终端：

```bash
python cli.py -h
python devcli.py -h
```

入口脚本（用户 CLI）：

```python
from core.infra.cli import Cli

Cli.user.bootstrap(__file__)
raise SystemExit(Cli.user.main())
```

入口脚本（开发 CLI）：

```python
from core.infra.cli import Cli

raise SystemExit(Cli.dev.main())
```

**预期结果：** 打印帮助或按 argv 执行对应命令，并以进程退出码结束。

---

## 下一步

- [API.md](./API.md)
- [glossary.yaml](./glossary.yaml)
- [README.md](./README.md)

```bash
python3 -m pytest core/infra/cli/__test__/ -q
```
