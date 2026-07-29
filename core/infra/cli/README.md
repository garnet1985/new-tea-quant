# infra.cli

NTQ 命令行 Facade：`Cli.user`（策略用户）与 `Cli.dev`（开发/运维），脚手架在 `Cli.shared`。

## 入口

```bash
python cli.py -h
python devcli.py -h
```

## 代码调用

```python
from core.infra.cli import Cli

Cli.user.bootstrap(__file__)
raise SystemExit(Cli.user.main())

raise SystemExit(Cli.dev.main())
```

`__init__.py` **只导出** `Cli`。契约见 `api.yaml`。
