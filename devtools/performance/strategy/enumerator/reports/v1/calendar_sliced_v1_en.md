# NTQ Calendar-Sliced Enumerator Performance Report

> **Version**: v1
> **Mode**: calendar_sliced (Cross-sectional Backtesting)
> **Data File**: [calendar_sliced_v1.json](./calendar_sliced_v1.json)
> **Last Updated**: 2026-06-22

---

## 📊 Core Performance Metrics (5,596 Stocks)

### Time Efficiency

| Metric | Value | Unit | Notes |
|:-------|:-----:|:----:|:------|
| **Wall Clock Time** | **86.98** | seconds | Full test duration |
| **Wall Clock Time** | **1.45** | minutes | Same as above |
| **Processing Speed** | **64.3** | stocks/sec | Based on sample size |

### Architecture Configuration (Reader-Compute Model)

| Parameter | Value | Description |
|:----------|:-----:|:------------|
| **Reader Workers** | **7** | Data loading processes |
| **Compute Workers** | **1** | Strategy computation process (fixed) |
| **Queue Depth** | **8** | Queue capacity |
| **Prefetch** | **Enabled** | Pre-fetch switch |
| **Slice Open Days** | **63** | Trading days per slice |
| **Total Slices** | **12** | Total slice count |
| **Memory Budget** | **7,502.6 MB** | Memory budget |
| **Preload Depth** | **4** | Actual preload depth |
| **MB/Slice** | **46.1 MB** | Estimated size per slice |

### IO / Compute Analysis

| Metric | Value | Unit | Notes |
|:-------|:-----:|:----:|:------|
| **Total IO Time** | **142.48** | seconds | All Reader processes cumulative |
| **Total Compute Time** | **60.67** | seconds | Compute process cumulative |
| **Avg IO/Slice** | **11.87** | seconds | Avg data load time per slice |
| **Avg Compute/Slice** | **5.06** | seconds | Avg computation time per slice |
| **IO : Compute Ratio** | **2.35 : 1** | IO intensity indicator |
| **Peak RSS** | **5,982.2** | MB | Peak memory usage |
| **Total Payload** | **527.5** | MB | Total data transfer volume |

### Bottleneck Assessment

✅ **IO-bound workload** (IO > 2× Compute)  
✅ **Prefetch strategy effective** (IO > Compute, overlap possible)

---

## 📈 Per-Slice Time Breakdown

| Slice Index | IO Time (s) | Compute Time (s) | RSS (MB) | Payload (MB) |
|:-----------:|:-----------:|:----------------:|:--------:|:------------:|
| 0 | 19.300 | 6.954 | 4,312.9 | 43.2 |
| 1 | 12.173 | 4.871 | 4,307.7 | 43.8 |
| 2 | 11.725 | 4.917 | 4,095.6 | 45.3 |
| 3 | 12.245 | 5.053 | 3,901.4 | 45.8 |
| 4 | 11.782 | 4.998 | 3,664.7 | 46.1 |
| 5 | 12.130 | 5.154 | 3,559.9 | 46.0 |
| 6 | 12.053 | 5.167 | 4,959.8 | 46.0 |
| 7 | 9.398 | 5.301 | 5,904.3 | 46.3 |
| 8 | 15.911 | 5.192 | 5,982.2 | 46.5 |
| 9 | 9.614 | 5.183 | 5,698.8 | 46.6 |
| 10 | 9.634 | 5.069 | 5,558.7 | 46.1 |
| 11 | 6.515 | 2.809 | 5,442.1 | 25.7 |

**Observations**:
- Slice 0 initial load slower (19.3s), subsequent stable at ~11s
- Last slice (11) has smaller payload (25.7MB), likely boundary effect
- RSS fluctuates significantly (3.5GB - 6GB), related to GC and preloading

---

## 💾 Memory Usage

| Metric | Value | Unit | Notes |
|:-------|:-----:|:----:|:------|
| **Start Memory** | 152.0 | MB | Test start |
| **End Memory** | 68.5 | MB | Test end |
| **Memory Delta** | **-83.4** | MB | Memory released |
| **Peak RSS** | **5,982.2** | MB | Runtime peak |

**Memory Characteristic**: Slice mode processes one time-point at a time and releases memory afterward, resulting in negative overall delta.

---

## 🔍 Comparison with Stock-Based Mode

### Performance Under Same Conditions

| Dimension | Calendar-Sliced | Stock-Based (Optimal) | Ratio |
|:----------|:--------------:|:---------------------:|:-----:|
| **Wall Time** | **86.98s** | **27.66s** | **3.14x slower** |
| **Process Config** | Reader=7, Compute=1 | 8 workers, epj=5 | - |
| **Parallelism** | Time-slice parallel + batch | Stock-batch parallel | - |
| **Memory Delta** | -83.4 MB | +21.6 MB | Sliced is more efficient |
| **IO Profile** | IO-intensive (2.35:1) | IO-intensive (batch optimized) | - |

### Use Case Comparison

| Scenario | Recommended Mode | Reason |
|:---------|:---------------:|:-------|
| Factor screening, cross-sectional | ✅ **Sliced** | Natural time-point processing |
| Industry rotation, periodic rebalance | ✅ **Sliced** | Matches rebalancing cycle |
| Event-driven, technical signals | ✅ **Stock-Based** | Needs full history path |
| Large-scale screening (>2000 stocks) | ✅ **Sliced** | Memory-friendly |
| Complex strategy logic | ✅ **Stock-Based** | Higher flexibility |

---

## 📈 Performance Position (see [BENCHMARKS.md](../../BENCHMARKS.md))

Based on current single Compute process test:

| Tier | Throughput Range | Framework/Config |
|:----:|:----------------:|:------------------|
| T1 | > 500K/s | VectorBT (~700K/s) |
| T2 | 100K - 500K/s | NTQ Stock-Based (**126K/s**) |
| T3 | 50K - 100K/s | Zipline (~79K/s), Backtrader (~50K/s) |
| **T3-T4** | **40-100K/s** | **NTQ Sliced (current)** ← Current position |

**Note**: Slice mode currently at T3-T4 boundary. Limited by single Compute process configuration.

---

## 🎯 Performance Rating

| Dimension | Score | Weight | Weighted Score | Notes |
|:----------|:-----:|:------:|:-------------:|:------|
| **Architecture Design** | **8.5** | 20% | **1.70** | Reader-Compute separation, Prefetch effective |
| **Scalability** | **8.0** | 20% | **1.60** | Naturally supports time-dimension parallelism |
| **Stability** | **9.0** | 20% | **1.80** | Zero crashes, memory safe |
| **Resource Efficiency** | **7.5** | 20% | **1.50** | IO-intensive but Prefetch effective |
| **Maintainability** | **8.5** | 10% | **0.85** | Clean code, modular design |
| **Documentation** | **8.0** | 10% | **0.80** | Basic documentation available |
| **Total** | - | **100%** | **8.25/10** | - |

**Overall Rating**: 8.25/10

**Confidence Level**: ✅✅✅✅✅ High (based on 5,596 stocks × 12 slices experiment)

---

## 🚀 Optimization Recommendations

### P0 - Critical Tasks (This Week)

| Priority | Optimization | Expected Benefit | Effort | ROI |
|:--------:|:------------|:----------------:|:------:|:---:|
| **P0-1** | **Multi-Compute Process Test** | Validate optimal worker config | 1 day | ⭐⭐⭐⭐⭐ |
| **P0-2** | **Reader Workers Optimization** | Adjust reader count for IO profile | 0.5 day | ⭐⭐⭐⭐ |
| **P0-3** | **Queue Depth Experiment** | Find optimal queue depth | 0.5 day | ⭐⭐⭐⭐ |

### P1 - Important Tasks (This Month)

| Priority | Optimization | Expected Benefit | Effort | ROI |
|:--------:|:------------|:----------------:|:------:|:---:|
| **P1-1** | **Local DB (DuckDB) Integration** | Reduce IO latency 3-5x | 3 days | ⭐⭐⭐⭐⭐ |
| **P1-2** | **Dynamic Preload Adjustment** | Adjust depth based on real-time load | 2 days | ⭐⭐⭐⭐ |
| **P1-3** | **Different Rebalance Period Tests** | Monthly/quarterly performance comparison | 1 day | ⭐⭐⭐ |

---

## 📋 Test Environment & Configuration

### Hardware Environment

| Component | Spec | Impact Assessment |
|:----------|:-----|:------------------|
| **CPU** | Apple Silicon / Intel Multi-core | Sufficient (not bottleneck) |
| **Memory** | 16GB+ RAM | Abundant (low usage) |
| **Storage** | SSD (solid-state drive) | Fast local I/O |
| **Network** | LAN → MySQL remote (~8ms latency) | Key bottleneck source! |

### Software Environment

| Component | Version/Config | Notes |
|:----------|:--------------:|:------|
| **OS** | macOS (latest) | Dev machine |
| **Python** | 3.9+ | Runtime |
| **Database Engine** | MySQL 8.x (InnoDB) | Production-grade |
| **Database Type** | **Remote access** (network-bound) | Main performance limitation |
| **NTQ Version** | Development (latest commit) | Includes batch loading optimization |

### Data Scale

```
┌─────────────────────────────────────────────┐
│              Test Data Scale                 │
├─────────────────────────────────────────────┤
│  Stock Pool:    5,596 A-shares (PIT full)    │
│  Time Range:    2023-01-01 ~ 2025-12-31       │
│  Trading Days:  ~730 days (~3 years)         │
│  K-line Count:  ~3,492,271 records           │
│  Avg K-lines/stock: ~624 records            │
│  Slice Count:   12 slices × 63 days/slice    │
│  Data Sources:  5 (K-line + indicators +     │
│                  moneyflow + adjfactor + Tag) │
└─────────────────────────────────────────────┘
```

---

## 📝 Conclusions

### Current Status

✅ **Baseline established** - Slice mode fully operational, all metrics captured  
✅ **Architecture validated** - Reader-Compute separation effective, Prefetch working  
✅ **Data completeness achieved** - Per-Slice breakdown complete (12 slices)

### Performance Summary

| Dimension | Conclusion | Status |
|:----------|:----------|:------:|
| **Functional Completeness** | Can complete sliced enumeration tasks | ✅ Acceptable |
| **Memory Efficiency** | Memory-friendly, supports large-scale data | ✅ Acceptable |
| **IO Optimization** | Prefetch effective, IO/Compute = 2.35:1 | ✅ Acceptable |
| **Single-Process Speed** | 3.14x slower than Stock-Based | ⏳ Pending Optimization |
| **Parallelism Potential** | Naturally supports time-dimension parallelism | ✅ High Potential |
| **Data Collection** | Complete Per-Slice metrics | ✅ Acceptable |

### Final Verdict

**Meets basic usability standard**, architecture is reasonable, Prefetch strategy effective.

Current Position: **T3-T4 (boundary)** → Expected Post-Optimization: **T2-T3**

---

**Report Generated**: 2026-06-22T20:22:26+08:00
