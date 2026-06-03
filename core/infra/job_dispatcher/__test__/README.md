# job_dispatcher 测试

```bash
pytest core/infra/job_dispatcher/__test__/ -q
```

| 文件 | 覆盖 |
|------|------|
| `test_job_dispatcher.py` | QUEUE/BATCH、optional prepare、失败阶段、thread/process 池 |
| `test_probe.py` | auto / cap / clamp |

集成测试（Tag / Strategy）在业务模块 `__test__` 中。
