---
title: 用户空间隔离
aliases:
  - userspace
  - isolation
  - core
  - extension
  - 用户空间
  - 隔离
summary: core 升级可覆盖，userspace 保留；策略与扩展分别放哪。
---

# 用户空间隔离

NTQ 把框架和你的东西分开：

- **`core/`**：框架，升级时整体替换
- **`userspace/`**：策略、扩展、配置、运行时状态，升级时保留

## 目录

```
userspace/
├── strategies/              策略（不在 extensions 里）
├── extensions/
│   ├── adapters/            扫描后处理
│   ├── tags/                标签
│   ├── data_source/handlers/  数据源（运行时扫 handlers/）
│   ├── data_contract/       自定义数据契约
│   ├── assistant/           助手供应商
│   └── tables/              自定义表
└── system/
    ├── config/              覆盖默认配置
    ├── db/                  数据库文件
    ├── backup/
    └── updater/
```

userspace 根目录按顺序找：环境变量 `NEW_TEA_QUANT_USERSPACE_ROOT` 或 `NTQ_USERSPACE_ROOT` → `.ntq/userspace-path.json` → 项目下的 `userspace/`。

## 配置合并

```
core/default_config/...  →  userspace/system/config/...  →  环境变量
```

`data.json`、`worker.json`、`database/*.json` 深度合并。策略 `settings.py` 不合并。

## 扩展约定

| 类型 | 路径 |
| --- | --- |
| 适配器 | `userspace/extensions/adapters/<name>/adapter.py` |
| 标签 | `userspace/extensions/tags/<path>/` |
| 数据契约 | `userspace/extensions/data_contract/<key>/` |
| 数据源 | `userspace/extensions/data_source/handlers/` |

框架按约定发现这些目录，你不必改框架代码。

## 升级

- `core/` 换成新版本
- `userspace/` 不动
- 升级后会把升级器同步到 `userspace/system/updater/`
- 你的配置和策略不受影响

初始化可从 `initialization/userspace/userspace.zip` 解压；分发包会去掉 `.ntq`、`results/`、缓存和密钥。
