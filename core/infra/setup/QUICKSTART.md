# Setup — 快速开始

**模块：** `setup` · **版本：** `0.1.0`

最短路径：判断 CLI 是否需要安装，需要则跑安装编排。

---

## 最小示例

```python
from core.infra.setup import Setup

Setup.env.to_root_dir()
if Setup.runtime.needs_install("cli"):
    Setup.runtime.install_cli()
```

**预期结果：** 未就绪时执行 `core/infra/setup/core/steps/` 流水线；已就绪则 `needs_install` 为 `False`。

根目录入口等价于：

```bash
python install.py      # CLI 安装
python launcher.py     # UI 安装 + 启动
```

---

## 下一步

- [API.md](./API.md)

```bash
python3 -m pytest setup/__test__/test_api.py -q
```
