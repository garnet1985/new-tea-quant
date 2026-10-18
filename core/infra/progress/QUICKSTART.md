# Progress — 快速开始

**版本：** `0.2.0`

```python
from core.infra.progress import Progress

Progress.start("scan-1", job="scan", label="扫描")
Progress.tick("scan-1", 4, 10, detail="扫描 4/10")
Progress.finish("scan-1")

root = Progress.read("scan-1")
# root["ratio"] 为 1，root["status"] 为 completed
```

多层步骤只把子节点的 id 交给 tick。文件写在 userspace 临时目录的 `progress/scan-1.json`。

```python
Progress.start(
    "run-1",
    job="renew",
    label="更新数据",
    steps=[{"id": "run-1:daily", "label": "日线"}],
)
Progress.tick("run-1:daily", 4, 10, detail="抓取 4/10")
```
