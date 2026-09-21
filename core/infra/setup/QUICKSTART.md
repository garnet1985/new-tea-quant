# Setup — 快速开始

**模块：** `setup` · **版本：** `0.1.1`

最短路径：判断 CLI 是否需要安装，需要则跑安装编排。

---

## 最小示例

```python
from core.infra.setup import Setup

Setup.env.to_root_dir()
if Setup.runtime.needs_install("cli"):
    Setup.runtime.install_cli()
```

**预期结果：** 未就绪时执行 `core/infra/setup/core/steps/` 流水线；已就绪则 `needs_install` 为 `False`。完成后 `.ntq/setup-runtime.json` 的 `isReady` 为 `true`，刷新 UI 向导也显示已完成。

根目录入口等价于：

```bash
python install.py      # CLI 安装（显式执行；已装过也会再跑步骤）
python install.py --userspace /data/ntq --db duckdb
python install.py --db postgresql --db-host 127.0.0.1 --db-name ntq --db-user postgres --db-password secret
# 国内自动走清华 PyPI 镜像；可用 USE_CHINA_MIRROR=1/0 强制
python launcher.py     # UI 安装 + 启动
```

省略 `--userspace` / `--db` 走默认（仓库根下 `userspace/` + DuckDB）。带了参数就必须按参数执行，失败则停止并报错。不询问。

---

## 下一步

- [API.md](./API.md)

```bash
python3 -m pytest setup/__test__/test_api.py -q
```
