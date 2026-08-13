# 依赖安装风险检测（dependency_risk）

位置：`core/infra/cli/dev/scripts/dependency_risk/`（经 `devcli` 调用；**无**独立 `devtools/` 树）。

## 怎么跑

```bash
# 经 devcli（以 `python devcli.py -h` 当前别名为准）
python devcli.py check-deps
# 或模块入口
python -m core.infra.cli.dev.scripts.dependency_risk
python -m core.infra.cli.dev.scripts.dependency_risk --ci-mode
```

`devcli.py p` / pack 流程里可能自动跑依赖风险检查（见 publish_prep / pack 实现）。

## 检测什么

| 类 | 说明 |
|----|------|
| 需 C 编译器的包 | 安装失败风险（尤其 Windows） |
| 平台 / wheel 风险 | 可能缺预编译包 |
| 未使用依赖等 | 警告级提示 |

实现见同目录 `dependency_risk.py`。历史迁移笔记（旧 `devtools/...` 路径）已删除；以本文件与代码为准。
