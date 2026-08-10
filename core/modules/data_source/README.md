# Data Source 模块（`modules.data_source`）· **版本 0.4.0**

> 公开 API：[API.md](./API.md) · 快速开始：[QUICKSTART.md](./QUICKSTART.md)  
> 包根仅 `DataSourceManager`；基类见 `contracts.py`

从 **`userspace/data_source/mapping.py`** 与各 handler **`config.py`** 驱动抓取：加载表 schema、实例化 Handler / Provider，由调度器按依赖拓扑执行并写库（`is_dry_run` 可跳过写入）。

## 快速开始

见 [QUICKSTART.md](./QUICKSTART.md)。

## 目录结构

```text
core/modules/data_source/
├── module_info.yaml / API.md / QUICKSTART.md / README.md
├── contracts.py
├── core/                       # 实现层
│   ├── data_source_manager.py
│   ├── execution_scheduler.py
│   ├── base_class / data_class / catalog / service / dev /
│   └── **/__test__/
├── __test__/                   # 公开 API 契约测
└── docs/
```

## 依赖

- **`modules.data_manager`**
- **`infra.project_context`**
- **`infra.discovery`**

## 测试

见 [`__test__/TEST_CASES.md`](__test__/TEST_CASES.md)。

## 相关文档

- [架构](docs/ARCHITECTURE.md)
- [设计](docs/DESIGN.md)
- [API](API.md)
- [glossary](glossary.yaml)
