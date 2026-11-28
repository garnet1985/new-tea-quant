# Discovery — 架构

**模块：** `infra.discovery` · **版本：** `0.2.2`

**最低支持核心版本：** `>=0.5.0`

统一发现基础设施：门面 `Discovery` + 实现包 `core/`。词条见 [glossary.yaml](../glossary.yaml)。

---

## 职责与边界（结论）

**负责**

- 单文件查找 / 读写（JSON、YAML、文本、Python 配置变量）
- 目录树批量发现文件与目录
- 按包路径与命名模式发现子类、模块级对象；可选进程内缓存

**不负责**

- 业务基类定义（data_source / strategy / tag 等）
- 配置热更新、文件监视、跨进程缓存失效
- 把 `core/` 内部路径长期当作跨模块公开 API

---

## 模块结构图

```text
core/infra/discovery/
├── discovery.py          # 门面 Discovery
├── contracts.py          # DiscoveryConfig / DiscoveryResult / …
├── __init__.py           # 仅导出 Discovery
├── API.md / QUICKSTART.md / glossary.yaml / module_info.yaml
├── core/                 # 实现
│   ├── namespaces.py
│   ├── discovery_constants.py
│   ├── file_utils.py
│   ├── file_discovery.py
│   ├── class_discovery.py
│   ├── module_discovery.py
│   └── __test__/         # 包内单测
├── __test__/             # 公开 API 测试 + TEST_CASES.md
└── docs/
```

---

## 架构图

```mermaid
flowchart TB
  Caller["调用方<br/>modules / bff / infra.ai"] --> Facade[Discovery]
  Facade --> FileNS[file]
  Facade --> DiscoverNS[discover]
  Facade --> ClassNS[class_discovery]
  FileNS --> FileUtils
  DiscoverNS --> FileDiscovery
  DiscoverNS --> ClassDiscovery
  DiscoverNS --> ModuleDiscovery
  ClassNS --> ClassDiscovery
  Caller -.->|类型注解| Contracts[contracts]
```

跨模块契约类型走 `contracts`；运行时扫描统一走 `Discovery` 命名空间。

---

## 数据流

```mermaid
flowchart LR
  subgraph subclasses["子类发现"]
    S1["Discovery.discover.subclasses"] --> S2[DiscoveryConfig]
    S2 --> S3["ClassDiscovery.discover"]
    S3 --> S4["子包 import + 筛选"]
    S4 --> S5["dict key to class"]
  end

  subgraph find_in_tree["按 key 定位文件"]
    F1["Discovery.file.find_in_tree"] --> F2["直达 base/key/file"]
    F2 --> F3["或 rglob **/key/file"]
    F3 --> F4["Path or None"]
  end

  subgraph py_load["受信 Python 加载"]
    P1["load_python_namespace"] --> P2["exec 命名空间"]
    P3["load_python_config"] --> P1
    P2 --> P4["提取 var_name"]
  end
```

---

## 相关文档

- [用户指南](./USER_GUIDE.md)
- [API.md](../API.md)
- [术语表](../glossary.yaml)
- [决策](./DECISIONS.md)