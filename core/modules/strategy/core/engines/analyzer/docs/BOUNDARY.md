# Analyzer vs modules.analysis — boundary

## modules.analysis（纯统计 / ML，无业务、无 I/O）

- table / column in → struct out
- **入口**：``Analysis.Classical.*``、``Analysis.ML.*``
- **位置**：``core/modules/analysis/``

## strategy/engines/analyzer（业务编排 + 叙事）

| 包 | 职责 |
|----|------|
| ``analyzer.py`` | Facade / API 暴露 |
| ``pipeline.py`` | 战役编排（``AttributionPipeline`` / ``RollingPipeline`` 只串步骤） |
| ``steps/campaign/`` | 战役归因主链路包 |
| ``steps/campaign/config/`` | 配置步：``AttributionConfig.for_layer`` |
| ``steps/campaign/plan/`` | 计划步：``AttributionPlan.for_layer`` |
| ``steps/campaign/execute/`` | 执行步：``ExecuteStep.for_layer`` |
| ``steps/campaign/gather/`` | 收集步：``GatherStep.for_layer`` |
| ``steps/campaign/attribute/`` | 归因步：``AttributeStep.for_layer`` |
| ``steps/campaign/summarize/`` | 总结步：``SummarizeStep.for_layer`` |
| ``steps/campaign/report/`` | 报告步：``CampaignReportStep.for_layer`` + ``CampaignPresenter`` |
| ``steps/campaign/persist/`` | 落盘步：``PersistStep.for_layer`` + ``AttributionGroupStore`` |
| ``steps/campaign/trades/`` | spa 单笔铺平：``TradesStep.for_layer``（仅价格层有实质工作） |
| ``steps/rolling/`` | 滚动验证（窗口展开 / 总结 / 展示） |

Analyzer 担任归因职责。公开入口按层：``attribute_enumerate`` / ``attribute_price`` / ``attribute_portfolio``（CLI ``sea`` / ``spa`` / ``soa``）。须已有主 version；对照格写副本 ``{vid}-{r}``。战役口径见 [ATTRIBUTION_CAMPAIGN.md](../../../../docs/notes/ATTRIBUTION_CAMPAIGN.md)。``Analyzer.rolling`` 走 ``RollingPipeline``。单 version 的 prepare / analyze / report / layer 已删除。

## 入口（当前）

```text
Analyzer.attribute_*(key) → AttributionPipeline(kind=…) → steps/campaign/
Analyzer.rolling(key)     → RollingPipeline → steps/rolling/
```

``Strategy.simulate`` 只回测，不归因。战役报告写在 ``results/attribution/{n}/{enumerate|price_factor|portfolio}/``，滚动写 ``rolling/``。CLI ``sea`` / ``spa`` / ``soa`` / ``sw``。

## 依赖方向

```text
Analyzer.attribute_* / Analyzer.rolling → pipeline → campaign/rolling → modules.analysis（spa trades / 统计）
```

``modules.analysis`` 禁止 import strategy。
