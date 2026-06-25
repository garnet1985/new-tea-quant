# Performance Benchmarks

> **Version**: v1
> **Last Updated**: 2026-06-22
> **Purpose**: Reference baselines for NTQ performance evaluation

---

## Baseline Data Points

All data from public benchmarks (event-driven frameworks, similar test conditions).

| Framework | Throughput* | Time (5000 stocks × 3yr) | Architecture | Notes |
|:----------|:----------:|:------------------------:|:------------|:------|
| **VectorBT** | ~700K/s | ~5s | Vectorized | Fastest for simple strategies |
| **vn.py** | ~100K/s | ~35s | Event-driven + C++ ext | Popular in China |
| **NTQ** | **126K/s** | **28s** | Event-driven + batch loading | Our framework |
| **Backtrader** | ~50K/s | ~70s | Event-driven, pure Python | Most popular (14K+ stars) |
| **Zipline** | ~79K/s | ~44s | Event-driven | Legacy, discontinued |

*\*Throughput in K-lines/second, approximate values from public tests*

---

## Performance Tiers (for Summary Reports)

Use this simple tier table in summary documents:

| Tier | Range (K-lines/s) | Level |
|:----:|:----------------:|:------|
| T1 | > 500K | High-performance (vectorized/GPU) |
| T2 | 100K - 500K | Above average |
| T3 | 50K - 100K | Average |
| T4 | < 50K | Below average |

---

## How to Reference

In summary reports, use this format:

```markdown
### Performance Position
| Tier | Framework | Throughput |
|:----:|:----------|:----------:|
| T2 | **NTQ (Ours)** | **126K/s** ← We are here |
| T3 | Backtrader | ~50K/s |
| T3 | Zipline | ~79K/s |
| T2 | vn.py | ~100K/s |
| T1 | VectorBT | ~700K/s |
```

---

## Data Sources

- [Qbot vs Backtrader/Zipline](https://adg.csdn.net/69533c775b9f5f31781bf93c.html) (2025)
- [LedgerMind Framework Comparison](https://theledgermind.com/backtesting-framework-comparison-2026/) (2026)
- [DolphinDB vs VNPY](https://docs.dolphindb.com/en/Tutorials/performance_and_feature_comparison_of_dolphinDB_backtesting_framework_and_other.html)

---

## Version History

| Version | Date | Changes |
|:-------:|:-----|:--------|
| v1 | 2026-06-22 | Initial version with 5 frameworks |
