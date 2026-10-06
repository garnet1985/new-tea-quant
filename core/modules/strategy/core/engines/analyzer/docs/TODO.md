# Analyzer — 架构说明

归因编排在 ``strategy/engines/analyzer``；统计 / ML 原语在 ``modules/analysis``。

边界详见 [docs/BOUNDARY.md](./BOUNDARY.md)。战役口径详见 [ATTRIBUTION_CAMPAIGN.md](../../../../docs/notes/ATTRIBUTION_CAMPAIGN.md)。

---

## 入口

| 场景 | 入口 |
|------|------|
| 战役 | ``Analyzer.attribute_*(key)`` / CLI ``sea`` ``spa`` ``soa`` |
| 滚动 | ``Analyzer.rolling(key)`` / CLI ``sw`` |
| 终端展示 | ``Analyzer.CampaignPresenter`` / ``Analyzer.RollingPresenter`` |

单次 ``simulate`` 不归因。须先有主 version；``-f`` 即回测 ``ignore_cache``。

---

## 战役主链路

```text
config → plan → execute → gather → attribute → summarize → report → persist
（spa 另跑 trades）
```

---

## 目录

```text
analyzer/
├── analyzer.py              # Facade: attribute_* / rolling
├── consts.py                # SCHEMA_VERSION
├── docs/BOUNDARY.md
├── pipeline.py              # AttributionPipeline / RollingPipeline
└── steps/
    ├── campaign/            # 同构包：config/plan/execute/gather/attribute/summarize/report/persist/trades
    └── rolling/             # 滚动：config / windows / summarize / present
```
