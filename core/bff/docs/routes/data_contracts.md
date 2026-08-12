# Data contracts BFF

**版本：** 0.1.0

契约见 [`core/ui/fed/src/pages/dataContractPage/API.md`](../../../ui/fed/src/pages/dataContractPage/API.md)（有则）。

## 目录

```text
core/bff/APIs/data/contracts/
  routes.py
  implementer.py
  helpers/contract_catalog.py
```

## 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/v1/data-contracts/list` | 分页契约目录（UI DTO） |
