# NTQ Performance Report

> **标准性能报告模板**  
> **版本**: v1.0  
> **最后更新**: {date}

---

## 📌 Executive Summary

| 项目 | 内容 |
|------|------|
| **报告类型** | {report_type} |
| **测试对象** | {test_subject} |
| **测试日期** | {test_date} |
| **总体评级** | {overall_rating} |
| **关键结论** | {key_finding} |

---

## 1️⃣ Baseline (基准)

### 1.1 Environment (测试环境)

#### Hardware
| Component | Specification |
|-----------|---------------|
| CPU | {cpu_info} |
| Memory | {memory_size} |
| Storage | {storage_type} |
| Network | {network_type} |

#### Software
| Component | Version/Config |
|-----------|----------------|
| OS | {os_version} |
| Python | {python_version} |
| Database Engine | {db_engine} |
| Database Type | {db_type} (Remote/Local) |

### 1.2 Configuration (配置参数)

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Execution Mode** | {execution_mode} | stock_based / calendar_sliced |
| **Sample Size** | {sample_size} | 股票池大小 |
| **Date Range** | {date_range} | 回测时间区间 |
| **Workers** | {workers} | 进程数 |
| **Entities Per Job** | {entities_per_job} | 每批处理股票数 |
| **Cache State** | {cache_state} | cold / warm |
| **Strategy** | {strategy_name} | 使用的策略名称 |

### 1.3 Data Scale (数据规模)

| Metric | Value | Unit |
|--------|-------|------|
| Total Stocks | {total_stocks} | stocks |
| Total Klines | {total_klines} | records |
| Avg Klines per Stock | {avg_klines_per_stock} | records/stock |
| Trading Days | {trading_days} | days |
| Data Sources | {data_sources_count} | sources |

**Data Sources Detail:**
| Source Name | Table | Records | Query Type |
|-------------|-------|---------|------------|
| {source_1} | {table_1} | {records_1} | PER_ENTITY / GLOBAL |
| {source_2} | {table_2} | {records_2} | PER_ENTITY / GLOBAL |
| ... | ... | ... | ... |

### 1.4 Baseline Metrics (基线指标)

| Metric | Baseline Value | Unit | Target | Status |
|--------|----------------|------|--------|--------|
| Wall Time | {baseline_wall_time} | s | < {target_time}s | ✅/⚠️/❌ |
| Throughput | {baseline_throughput} | Klines/s | > {target_throughput} Klines/s | ✅/⚠️/❌ |
| Parallelism | {baseline_parallelism} | x | > {target_parallelism}x | ✅/⚠️/❌ |
| Memory Delta | {baseline_memory_delta} | MB | < {target_memory} MB | ✅/⚠️/❌ |

**Baseline Definition**: 
- This baseline was established on {baseline_date}
- Test conditions: {baseline_conditions}
- Measurement method: {measurement_method}

---

## 2️⃣ Data (测试数据)

### 2.1 Primary Results (主要结果)

#### Core Performance Metrics
| Configuration | Wall Time (s) | Throughput (Klines/s) | Parallelism (x) | Memory Δ (MB) | Status |
|--------------|---------------|-----------------------|-----------------|---------------|--------|
| {config_1} | {time_1} | {throughput_1} | {parallelism_1} | {memory_1} | ✅/⚠️/❌ |
| {config_2} | {time_2} | {throughput_2} | {parallelism_2} | {memory_2} | ✅/⚠️/❌ |
| {config_3} | {time_3} | {throughput_3} | {parallelism_3} | {memory_3} | ✅/⚠️/❌ |

**Optimal Configuration**: `{optimal_config}` with **{improvement}% improvement** over baseline

#### Detailed Breakdown
```
┌─────────────────────────────────────────────────────────────┐
│ Time Distribution                                          │
├─────────────────────────────────────────────────────────────┤
│ ████████████████████░░░░░░░░░░░░░░░  IO Wait    ({io_pct}%) │
│ ░░░░░░░░░░░░░░████░░░░░░░░░░░░░░░  Compute   ({compute_pct}%)│
│ ░░░░░░░░░░░░░░░░░░░░░░░██░░░░░░░░  Overhead  ({overhead_pct}%)│
└─────────────────────────────────────────────────────────────┘
Total: {total_time}s
```

### 2.2 Comparative Analysis (对比分析)

#### vs Previous Version
| Metric | Current | Previous | Change | Improvement |
|--------|---------|----------|--------|-------------|
| Wall Time | {current_time} | {prev_time} | {time_delta}s | {time_improvement}% |
| Throughput | {current_throughput} | {prev_throughput} | {throughput_delta} | {throughput_improvement}% |
| Memory Usage | {current_memory} | {prev_memory} | {memory_delta} MB | {memory_improvement}% |

#### vs Competitors
| Framework | Wall Time | Throughput | Relative Speed | Notes |
|-----------|-----------|------------|----------------|-------|
| **NTQ (Ours)** | {ntq_time} | {ntq_throughput} | **1.0x** | Baseline |
| {competitor_1} | {comp1_time} | {comp1_throughput} | {comp1_ratio}x | {comp1_notes} |
| {competitor_2} | {comp2_time} | {comp2_throughput} | {comp2_ratio}x | {comp2_notes} |

### 2.3 Scaling Behavior (扩展性分析)

#### Data Size Scaling
| Stocks | Time (s) | Throughput | Scaling Efficiency |
|--------|----------|------------|-------------------|
| {size_1} | {time_size_1} | {throughput_size_1} | {efficiency_1} |
| {size_2} | {time_size_2} | {throughput_size_2} | {efficiency_2} |
| {size_3} | {time_size_3} | {throughput_size_3} | {efficiency_3} |

**Scaling Formula**: `Time = O({complexity})` where complexity is {linear/quadratic/sublinear}

#### Concurrency Scaling
| Workers × Entities/Job | Time (s) | Speedup | Efficiency |
|------------------------|----------|---------|------------|
| {config_a} | {time_a} | {speedup_a} | {eff_a}% |
| {config_b} | {time_b} | {speedup_b} | {eff_b}% |
| {config_c} | {time_c} | {speedup_c} | {eff_c}% |

**Optimal Point**: `{optimal_point}` with best cost-performance ratio

### 2.4 Resource Utilization (资源使用)

#### Memory Profile
| Phase | Start (MB) | Peak (MB) | End (MB) | Delta (MB) |
|-------|------------|-----------|----------|------------|
| Initialization | {mem_init_start} | {mem_init_peak} | {mem_init_end} | {mem_init_delta} |
| Data Loading | {mem_load_start} | {mem_load_peak} | {mem_load_end} | {mem_load_delta} |
| Computation | {mem_comp_start} | {mem_comp_peak} | {mem_comp_end} | {mem_comp_delta} |
| Output | {mem_out_start} | {mem_out_peak} | {mem_out_end} | {mem_out_delta} |

**Memory Safety Check**: ✅ No OOM / ⚠️ Near limit / ❌ OOM occurred

#### IO Statistics
| Metric | Count | Time (s) | Avg Latency (ms) |
|--------|-------|----------|------------------|
| DB Queries | {db_queries} | {db_time} | {db_latency} |
| File Reads | {file_reads} | {read_time} | - |
| File Writes | {file_writes} | {write_time} | - |
| Cache Hits | {cache_hits} | - | - |
| Cache Misses | {cache_misses} | - | - |

**Cache Hit Rate**: `{cache_hit_rate}%` (Target: > {target_cache_hit}%)

### 2.5 Raw Data Files (原始数据)

| File | Path | Description |
|------|------|-------------|
| Performance Report | {report_path} | JSON format detailed metrics |
| Experiment Log | {log_path} | Complete execution log |
| Strategy Config | {strategy_path} | Settings used for test |

---

## 3️⃣ Conclusions (结论与建议)

### 3.1 Key Findings (关键发现)

#### ✅ Validated Conclusions (已验证结论)

**Finding #1**: {finding_1_title}
- **Evidence**: {evidence_1_data}
- **Impact**: {impact_1}
- **Confidence**: High/Medium/Low (based on {sample_size} samples)

**Finding #2**: {finding_2_title}
- **Evidence**: {evidence_2_data}
- **Impact**: {impact_2}
- **Confidence**: High/Medium/Low

**Finding #3**: {finding_3_title}
- **Evidence**: {evidence_3_data}
- **Impact**: {impact_3}
- **Confidence**: High/Medium/Low

#### ⚠️ Hypotheses to Validate (待验证假设)

**Hypothesis #1**: {hypothesis_1}
- **Rationale**: {rationale_1}
- **Validation Method**: {validation_method_1}
- **Expected Outcome**: {expected_outcome_1}

**Hypothesis #2**: {hypothesis_2}
- **Rationale**: {rationale_2}
- **Validation Method**: {validation_method_2}
- **Expected Outcome**: {expected_outcome_2}

### 3.2 Performance Rating (性能评级)

| Dimension | Score (1-10) | Weight | Weighted Score | Notes |
|-----------|--------------|--------|----------------|-------|
| **Raw Speed** | {speed_score} | 25% | {speed_weighted} | {speed_notes} |
| **Scalability** | {scale_score} | 20% | {scale_weighted} | {scale_notes} |
| **Stability** | {stability_score} | 20% | {stability_weighted} | {stability_notes} |
| **Resource Efficiency** | {efficiency_score} | 15% | {efficiency_weighted} | {efficiency_notes} |
| **Maintainability** | {maintain_score} | 10% | {maintain_weighted} | {maintain_notes} |
| **Documentation** | {doc_score} | 10% | {doc_weighted} | {doc_notes} |
| **TOTAL** | - | **100%** | **{total_score}/10** | |

**Overall Grade**: {grade} ({total_score}/10)

**Grade Scale**:
- ⭐⭐⭐⭐⭐ (9-10): Exceptional - Industry leading
- ⭐⭐⭐⭐ (8-8.9): Excellent - Above average, production ready
- ⭐⭐⭐ (7-7.9): Good - Meets requirements, room for improvement
- ⭐⭐ (6-6.9): Acceptable - Works but needs optimization
- ⭐ (<6): Below standard - Requires significant work

### 3.3 Optimization Recommendations (优化建议)

#### 🔴 P0 - Critical (必须完成)

| Priority | Optimization | Expected Gain | Effort | ROI |
|----------|--------------|---------------|--------|-----|
| {p0_1_title} | {p0_1_detail} | +{p0_1_gain}% | {p0_1_effort} | ⭐⭐⭐⭐⭐ |
| {p0_2_title} | {p0_2_detail} | +{p0_2_gain}% | {p0_2_effort} | ⭐⭐⭐⭐ |

**Timeline**: {p0_timeline}  
**Owner**: {p0_owner}

#### 🟡 P1 - Important (应该完成)

| Priority | Optimization | Expected Gain | Effort | ROI |
|----------|--------------|---------------|--------|-----|
| {p1_1_title} | {p1_1_detail} | +{p1_1_gain}% | {p1_1_effort} | ⭐⭐⭐⭐ |
| {p1_2_title} | {p1_2_detail} | +{p1_2_gain}% | {p1_2_effort} | ⭐⭐⭐ |

**Timeline**: {p1_timeline}

#### 🟢 P2 - Nice to Have (可以做)

| Priority | Optimization | Expected Gain | Effort | ROI |
|----------|--------------|---------------|--------|-----|
| {p2_1_title} | {p2_1_detail} | +{p2_1_gain}% | {p2_1_effort} | ⭐⭐⭐ |

**Timeline**: {p2_timeline}

### 3.4 Action Items (行动项)

#### Immediate Actions (本周)
- [ ] **{action_1}**
  - Owner: {action_1_owner}
  - Due: {action_1_due}
  - Success Criteria: {action_1_criteria}

- [ ] **{action_2}**
  - Owner: {action_2_owner}
  - Due: {action_2_due}
  - Success Criteria: {action_2_criteria}

#### Short-term Goals (本月)
- [ ] {goal_1}
- [ ] {goal_2}
- [ ] {goal_3}

#### Long-term Vision (本季度)
- [ ] {vision_1}
- [ ] {vision_2}

### 3.5 Risk Assessment (风险评估)

| Risk | Probability | Impact | Mitigation | Status |
|------|-------------|--------|------------|--------|
| {risk_1} | {prob_1} | {impact_1} | {mitigation_1} | 🟢/🟡/🔴 |
| {risk_2} | {prob_2} | {impact_2} | {mitigation_2} | 🟢/🟡/🔴 |

### 3.6 Next Steps (下一步)

1. **Immediate**: {next_step_1}
2. **This Week**: {next_step_2}
3. **Next Sprint**: {next_step_3}

**Follow-up Meeting**: {followup_date}  
**Report Updated By**: {author}  
**Next Review Date**: {next_review_date}

---

## 📎 Appendix (附录)

### A. Test Methodology (测试方法)

#### A.1 Reproducibility Checklist
- [x] Fixed data set (same stocks, same date range)
- [x] Cold start (cache cleared before each run)
- [x] Isolated environment (minimal background processes)
- [x] Multiple runs (median of {n_runs} runs used)
- [x] Consistent configuration (settings documented)

#### A.2 Measurement Tools
- **Performance Profiler**: core/modules/strategy/engines/shared/performance_profiler.py
- **Time Measurement**: time.perf_counter() (wall clock)
- **Memory Tracking**: resource.getrusage() (RSS)
- **IO Monitoring**: Custom hooks in DataLoader

#### A.3 Calculation Formulas
```
Throughput = Total_Klines / Wall_Time_Seconds
Parallelism = Sum_Worker_Time / Wall_Time
Speedup = Baseline_Time / Optimized_Time
Efficiency = Speedup / Number_of_Workers
Cache_Hit_Rate = Cache_Hits / (Cache_Hits + Cache_Misses) * 100
```

### B. Historical Data (历史数据)

| Version | Date | Wall Time | Throughput | Key Changes |
|---------|------|-----------|------------|-------------|
| v{ver_1} | {date_1} | {time_1} | {throughput_1} | {changes_1} |
| v{ver_2} | {date_2} | {time_2} | {throughput_2} | {changes_2} |
| **Current** | **{date_current}** | **{time_current}** | **{throughput_current}** | **{changes_current}** |

### C. Glossary (术语表)

| Term | Definition |
|------|------------|
| **Wall Clock Time** | Actual elapsed time from start to finish |
| **Parallelism Factor** | Ratio of total CPU time to wall time (>1 indicates parallelism) |
| **Entities Per Job** | Number of stocks processed in a single batch |
| **Cold Start** | First run with empty cache (no pre-loaded data) |
| **PIT** | Point-In-Time (survivorship bias avoidance) |
| **QFQ** | Forward-adjusted quote (前复权) |
| **Calendar Slice** | Time-based cross-sectional processing mode |

### D. References (参考链接)

- **Source Code**: {code_link}
- **Strategy Definition**: {strategy_link}
- **Previous Reports**: {previous_report_links}
- **Related Documentation**: {doc_links}

---

## 📊 Report Metadata

| Field | Value |
|-------|-------|
| **Report ID** | {report_id} |
| **Generated At** | {generated_at} |
| **Generated By** | {generated_by} (Manual/Automated) |
| **Template Version** | v1.0 |
| **Classification** | Internal/Public/Confidential |
| **Review Status** | Draft/Reviewed/Approved |
| **Approval Signature** | {approver_signature} |

---

**End of Report**

*For questions or clarifications, contact: {contact_info}*
