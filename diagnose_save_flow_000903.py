#!/usr/bin/env python3
"""
诊断 000903.SZ 的 save 流程：定位问题在 Step1(report) 还是 Step2(process)

Step1 - Report: 产出的数据是否正确传递到 on_after_single_api_job_bundle_complete？
  - API 返回的 result 格式
  - _has_actual_data 是否通过
  - enrich 后的 result 内容

Step2 - Process: handler 收到的数据是否正确处理？
  - adj_factor 是否有数据
  - daily_kline 返回
  - qfq_kline 返回
  - qfq_price_map 是否为空
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
from core.modules.data_manager import DataManager
from core.infra.project_context import ConfigManager
from userspace.data_source.handlers.adj_factor_event.helper import AdjFactorEventHandlerHelper as helper
import pandas as pd


def main():
    stock_id = "000903.SZ"
    data_manager = DataManager(is_verbose=False)
    data_manager.initialize()

    # 获取 providers
    from core.modules.data_source.service.provider_helper import DataSourceProviderHelper
    tushare_provider = DataSourceProviderHelper.get_provider("tushare")
    akshare_provider = DataSourceProviderHelper.get_provider("akshare")

    if not tushare_provider or not akshare_provider:
        print("❌ providers 不可用")
        return

    end_date = data_manager.service.calendar.get_latest_completed_trading_date()
    default_start = ConfigManager.get_default_start_date()
    default_ymd = str(default_start).replace("-", "")[:8]
    end_ymd = str(end_date).replace("-", "")[:8]

    print("\n" + "=" * 70)
    print("【Step1 - Report】模拟 API 产出 → enrich → _has_actual_data")
    print("=" * 70)

    # 1. 拉 adj_factor（与真实流程一致）
    print(f"\n1. 调用 Tushare get_adj_factor({stock_id}, {default_ymd}~{end_ymd})...")
    try:
        adj_factor_result = tushare_provider.get_adj_factor(
            ts_code=stock_id,
            start_date=default_ymd,
            end_date=end_ymd,
        )
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        adj_factor_result = None

    raw_result = {"adj_factor": adj_factor_result}
    print(f"   raw_result keys: {list(raw_result.keys())}")
    if isinstance(adj_factor_result, pd.DataFrame):
        print(f"   adj_factor: shape={adj_factor_result.shape}, empty={adj_factor_result.empty}")
        if not adj_factor_result.empty:
            print(f"   前3行:\n{adj_factor_result.head(3)}")
    else:
        print(f"   adj_factor: type={type(adj_factor_result)}, value={adj_factor_result}")

    # 2. enrich（与 handler.enrich_result_for_batch 一致）
    enriched = dict(raw_result) if raw_result else {}
    enriched["last_update"] = end_ymd
    print(f"\n2. enrich 后: keys={list(enriched.keys())}, last_update={enriched.get('last_update')}")

    # 3. _has_actual_data 检查
    def _has_actual_data(result_dict):
        if not isinstance(result_dict, dict) or not result_dict:
            return False
        for job_id, result_data in result_dict.items():
            if result_data is None:
                continue
            if isinstance(result_data, pd.DataFrame):
                if not result_data.empty:
                    return True
            elif isinstance(result_data, (list, tuple)):
                if len(result_data) > 0:
                    return True
            elif result_data:
                return True
        return False

    passes_has_actual = _has_actual_data(enriched)
    print(f"\n3. _has_actual_data(enriched) = {passes_has_actual}")
    if not passes_has_actual:
        print("   ❌ Step1 失败：result 未通过 _has_actual_data，不会进入 batch_save")
        return
    print("   ✅ Step1 通过：会进入 batch_save，调用 on_after_single_api_job_bundle_complete")

    print("\n" + "=" * 70)
    print("【Step2 - Process】模拟 handler 全量保存逻辑")
    print("=" * 70)

    fetched_data = enriched
    adj_factor_result = fetched_data.get("adj_factor")

    if adj_factor_result is None or (isinstance(adj_factor_result, pd.DataFrame) and adj_factor_result.empty):
        print(f"\n2a. adj_factor 为空 → 走「仅更新 last_update」分支")
        print("   (表无该股时 update 影响 0 行)")
        return

    print(f"\n2a. adj_factor 有数据 ({adj_factor_result.shape[0]} 行) → 需全量")
    print("   调用 daily_kline + qfq_kline...")

    # 2b. daily_kline
    try:
        daily_kline_result = tushare_provider.get_daily_kline(
            ts_code=stock_id,
            start_date=default_ymd,
            end_date=end_ymd,
        )
    except Exception as e:
        print(f"   ❌ daily_kline 失败: {e}")
        daily_kline_result = None

    if daily_kline_result is None or (isinstance(daily_kline_result, pd.DataFrame) and daily_kline_result.empty):
        print(f"   ❌ daily_kline 为空 → 跳过")
        return
    print(f"   daily_kline: shape={daily_kline_result.shape}")

    # 2c. qfq_kline
    symbol_tx = helper.convert_to_tx_symbol(stock_id)
    print(f"   qfq_kline symbol={symbol_tx}")
    try:
        qfq_kline_result = akshare_provider.get_qfq_kline(
            symbol=symbol_tx,
            start_date=default_ymd,
            end_date=end_ymd,
        )
    except Exception as e:
        print(f"   ❌ qfq_kline 异常: {e}")
        qfq_kline_result = None

    print(f"   qfq_kline 返回: type={type(qfq_kline_result)}")
    if isinstance(qfq_kline_result, pd.DataFrame):
        print(f"   - DataFrame: shape={qfq_kline_result.shape}, empty={qfq_kline_result.empty}")
        if not qfq_kline_result.empty:
            print(f"   列: {list(qfq_kline_result.columns)}")
            print(f"   前3行:\n{qfq_kline_result.head(3)}")
    else:
        print(f"   - 非 DataFrame: {qfq_kline_result}")

    # 2d. parse qfq_price_map
    if isinstance(qfq_kline_result, pd.DataFrame):
        qfq_price_map = helper.parse_akshare_qfq_price_map(qfq_kline_result)
    else:
        qfq_price_map = helper.parse_eastmoney_qfq_price_map(qfq_kline_result or {})

    print(f"\n2d. qfq_price_map: len={len(qfq_price_map)}")
    if qfq_price_map:
        sample = list(qfq_price_map.items())[:3]
        print(f"   样例: {sample}")
        print("   ✅ Step2 通过：可继续 build_adj_factor_events 并保存")
    else:
        print("   ❌ Step2 失败：qfq_price_map 为空 → 跳过保存")
        print("   原因可能是：AKShare 列名不匹配、数据为空、或 parse 逻辑问题")

    print("\n" + "=" * 70)
    print("诊断完成")
    print("=" * 70)


if __name__ == "__main__":
    main()
