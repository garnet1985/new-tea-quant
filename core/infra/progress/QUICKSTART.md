# Progress 快速开始

**版本：** `0.1.0`

```python
from core.infra.progress import Progress

Progress.open("demo", 4, job="backtest")
Progress.step(2, 4, source="demo")
Progress.sub(3, 10)
print(Progress.read())
print(Progress.fraction(2, 4, 3, 10))
Progress.close()
```

比例是 `(2 + 3/10) / 4`。文件写在 userspace 的临时目录 `progress.json`。
