# entity_based

## 目录职责

| 文件 | 进程 | 职责 |
|------|------|------|
| **`pipeline.py`** | 主进程 | 完整流程：preprocess → BacktestEngine → postprocess |
| **`worker.py`** | 子进程 | init / execute / release |
| `executor.py` | 子进程 | 单股 open_dates scan（待 review） |
| `resolver/jobs.py` | 主进程 | 构建每股 job（待 review） |
| `context/runtime.py` | 主进程 | RuntimeContext + 性能基线 |
| `context/data.py` | hook | DataContext |
| `context/status.py` | 主进程 | RuntimeStatus |

## 入口

```
EnumeratorEngine.run
  └─ entity_based/pipeline.py :: EntityBasedJobPipeline.run
       ├─ build_runtime
       ├─ execute_backtest → BacktestEngine.entity_based.run(EntityBasedWorker)
       └─ postprocess（opportunities / report）
```

## 子进程

```
EntityBasedWorker.on_init      batch load + cursor
EntityBasedWorker.execute      → EntityBasedExecutor
EntityBasedWorker.on_release   释放 session
```
