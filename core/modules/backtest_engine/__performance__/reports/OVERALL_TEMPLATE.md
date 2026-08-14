# 性能总览 — {{:mode_label}}

- 生成时间: {{:generated_at}}
- BE: {{:be_version}}
- 模式: {{:mode}}
- 模型: 墙钟 T ≈ T0 + k·N（N=股票数，交易日固定）

## 结论（先看这）

{{:verdicts_section}}

## 分库明细

{{:engines_detail_section}}

## 怎么读

- 吞吐随 N **上升**：固定成本被摊薄（「越大越划算」）。
- 吞吐大致 **持平**：墙钟近似按股线性。
- 吞吐 **下降**：越大越慢，查调度/IO/内存/片宽。
- T0 是 sink（进程、规划、采样等）；占比随 N 变大应下降。
- entity 与 slice 分看，不要横比谁更快。
