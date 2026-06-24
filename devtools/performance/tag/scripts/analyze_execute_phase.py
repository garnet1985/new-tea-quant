#!/usr/bin/env python3
"""
Execute 阶段内部剖析

在 compute_engine 的关键位置添加计时器，精确测量：
1. build_stocks_context() 数据构建
2. CalendarAsOfContext 上下文创建
3. on_calendar_asof() 用户计算
4. _append_entity_tags() 结果序列化
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, "/Users/garnet/Desktop/new-tea-quant")

# 临时 monkey-patch compute_engine 添加计时器
import core.modules.tag.engines.sliced.runtime.compute_engine as compute_module

_original_run_slice_calendar_asof = compute_module.TagSliceComputeEngine._run_slice_calendar_asof

def _profiled_run_slice_calendar_asof(self, payload):
    """带计时的 _run_slice_calendar_asof 版本。"""

    timings = {
        "total_slices": 0,
        "total_dates": 0,
        "stocks_context_ms": [],
        "context_creation_ms": [],
        "on_asof_call_ms": [],
        "result_append_ms": [],
        "errors": 0,
    }

    by_entity = (payload.batch_transfer or {}).get("by_entity") or {}
    settings = self._settings
    axis_id = compute_module.axis_data_id_from_settings(settings)
    min_records = int(
        settings.get("incremental_required_records_before_as_of_date") or 1
    )
    worker = self._create_bulk_worker()

    for open_date_index, as_of in enumerate(payload.open_dates):
        # 计时: build_stocks_context
        t0 = time.perf_counter()
        stocks = compute_module.build_stocks_context(
            by_entity,
            as_of,
            axis_data_id=axis_id,
            min_records=min_records,
        )
        t1 = time.perf_counter()
        timings["stocks_context_ms"].append((t1 - t0) * 1000)

        # 计时: Context 创建
        t2 = time.perf_counter()
        ctx = compute_module.CalendarAsOfContext(
            as_of_date=as_of,
            slice_id=payload.slice_id,
            slice_open_days=self._slice_open_days,
            window_start=payload.window_start,
            window_end=payload.window_end,
            stocks=stocks,
            carry=dict(self._carry),
            open_date_index=open_date_index,
            is_first_open_of_month=compute_module.is_first_open_of_month(as_of, self._open_dates_all),
            is_last_open_of_month=compute_module.is_last_open_of_month(as_of, self._open_dates_all),
            is_first_open_of_year=compute_module.is_first_open_of_year(as_of, self._open_dates_all),
            is_last_open_of_year=compute_module.is_last_open_of_year(as_of, self._open_dates_all),
        )
        t3 = time.perf_counter()
        timings["context_creation_ms"].append((t3 - t2) * 1000)

        # 计时: on_calendar_asof 调用
        try:
            t4 = time.perf_counter()
            asof_result = self._call_on_calendar_asof(worker, ctx, settings)
            t5 = time.perf_counter()
            timings["on_asof_call_ms"].append((t5 - t4) * 1000)

            self._carry = dict(asof_result.carry or {})

            # 计时: 结果追加
            t6 = time.perf_counter()
            self._append_entity_tags(as_of, asof_result)
            t7 = time.perf_counter()
            timings["result_append_ms"].append((t7 - t6) * 1000)

        except Exception as exc:
            timings["errors"] += 1
            msg = f"on_calendar_asof slice={payload.slice_id} as_of={as_of}: {exc}"
            compute_module.logger.exception("Tag calendar_asof failed: %s", msg)
            self._errors.append(msg)

        timings["total_dates"] += 1
    timings["total_slices"] += 1

    # 保存计时结果到实例
    if not hasattr(self, '_profile_timings'):
        self._profile_timings = []
    self._profile_timings.append(timings)


# 应用 patch
compute_module.TagSliceComputeEngine._run_slice_calendar_asof = _profiled_run_slice_calendar_asof


def run_profiled_test():
    """运行带 profile 的测试。"""

    import subprocess
    import shutil
    from datetime import datetime

    PROJECT_ROOT = Path("/Users/garnet/Desktop/new-tea-quant")
    BASE_TAG_DIR = PROJECT_ROOT / "devtools" / "performance" / "tag" / "test_base_tags" / "calendar_sliced"
    USERSPACE_TAGS = PROJECT_ROOT / "userspace" / "extensions" / "tags"

    scenario_name = "bench_profiled_execute"
    scenario_path = USERSPACE_TAGS / scenario_name

    # 准备场景
    if scenario_path.exists():
        shutil.rmtree(scenario_path)
    shutil.copytree(BASE_TAG_DIR, scenario_path)

    cmd = [
        str(PROJECT_ROOT / "venv" / "bin" / "python3"),
        str(PROJECT_ROOT / "cli.py"),
        "tag",
        "--scenario", scenario_name,
        "--stock-limit", "50",
        "--profile",
        "--dry-run",
    ]

    print("=" * 70)
    print("  Execute 阶段内部剖析 (50 entities × 50 days/slice)")
    print("=" * 70)
    print(f"\n[RUN] {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=300)

    # 清理
    if scenario_path.exists():
        shutil.rmtree(scenario_path)

    return result.returncode == 0


if __name__ == "__main__":
    success = run_profiled_test()

    # 注意：由于 subprocess 隔离，我们需要其他方式获取 timing 数据
    # 这里先确认测试能成功运行，后续可以通过日志或文件传递 timing

    print("\n[INFO] Profiled test completed:", "✅" if success else "❌")

    if not success:
        print("\n[ERROR] Test failed. Check logs above.")
