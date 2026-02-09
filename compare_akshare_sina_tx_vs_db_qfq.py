#!/usr/bin/env python3
"""
对比 AKShare 新浪/腾讯 前复权 vs DB load_qfq

说明：
- stock_zh_a_hist_sina 在当前 AKShare 1.17.26 中不存在
- 改用 stock_zh_a_hist_tx（腾讯数据源 gu.qq.com），支持 qfq/hfq
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def tushare_to_tx_symbol(stock_id: str) -> str:
    """000001.SZ -> sz000001, 600000.SH -> sh600000"""
    if "." not in stock_id:
        return stock_id
    code, market = stock_id.split(".")
    if market == "SZ":
        return f"sz{code}"
    elif market == "SH":
        return f"sh{code}"
    elif market == "BJ":
        return f"bj{code}"
    return stock_id


def fetch_akshare_tx_qfq(stock_id: str, start_date: str, end_date: str) -> dict:
    """
    从 AKShare stock_zh_a_hist_tx（腾讯）获取前复权收盘价
    返回 {date_ymd: close}
    """
    try:
        import akshare as ak
    except ImportError:
        print("  AKShare: 未安装")
        return {}

    tx_symbol = tushare_to_tx_symbol(stock_id)
    try:
        df = ak.stock_zh_a_hist_tx(
            symbol=tx_symbol,
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )
    except Exception as e:
        print(f"  AKShare 腾讯: 拉取失败 {e}")
        return {}

    if df is None or df.empty:
        return {}

    result = {}
    # 腾讯返回列名可能是 日期/date, 收盘/close
    date_col = "日期" if "日期" in df.columns else ("date" if "date" in df.columns else None)
    close_col = "收盘" if "收盘" in df.columns else ("close" if "close" in df.columns else None)
    if not date_col or not close_col:
        print(f"  AKShare 腾讯: 列名异常 {list(df.columns)}")
        return {}

    for _, row in df.iterrows():
        d = str(row.get(date_col, ""))
        d_ymd = d.replace("-", "") if d else ""
        if len(d_ymd) == 8 and d_ymd.isdigit():
            c = float(row.get(close_col, 0))
            if c > 0:
                result[d_ymd] = c
    return result


def main():
    # 至少 20 只股票，覆盖沪市、深市、不同行业
    stocks = [
        "000001.SZ", "000002.SZ", "000333.SZ", "000858.SZ", "002415.SZ",  # 平安银行、万科A、美的、五粮液、海康
        "300059.SZ", "300750.SZ", "600000.SH", "600036.SH", "600519.SH",  # 东财、宁德、浦发、招行、茅台
        "600030.SH", "601318.SH", "601398.SH", "000651.SZ", "002304.SZ",  # 中信、平安、工行、格力、洋河
        "603259.SH", "601012.SH", "000725.SZ", "002475.SZ", "300274.SZ",  # 药明、隆基、京东方、立讯、阳光电源
    ]
    start_ymd = "20240102"
    end_ymd = "20240131"

    print("=" * 70)
    print("AKShare stock_zh_a_hist_tx（腾讯） 前复权 vs DB load_qfq")
    print("=" * 70)
    print("说明：stock_zh_a_hist_sina 在当前版本不存在，改用腾讯数据源")
    print(f"股票: {len(stocks)} 只")
    print(f"时间段: {start_ymd} ~ {end_ymd}")
    print()

    from core.modules.data_manager import DataManager

    data_mgr = DataManager(is_verbose=False)
    data_mgr.initialize()

    # 汇总统计
    summary = []  # (stock_id, avg_pct, match_count, total_count)

    for stock_id in stocks:
        tx_map = fetch_akshare_tx_qfq(stock_id, start_ymd, end_ymd)
        if not tx_map:
            summary.append((stock_id, None, "腾讯无数据"))
            continue

        try:
            db_klines = data_mgr.stock.kline.load_qfq(
                stock_id, term="daily", start_date=start_ymd, end_date=end_ymd
            )
        except Exception as e:
            summary.append((stock_id, None, f"DB错误: {e}"))
            continue

        db_map = {}
        for row in db_klines:
            d = row.get("date")
            if d:
                d_ymd = str(d).replace("-", "")
                qfq_close = row.get("qfq_close")
                if qfq_close is not None:
                    db_map[d_ymd] = float(qfq_close)

        if not db_map:
            summary.append((stock_id, None, "DB无数据"))
            continue

        common_dates = sorted(set(tx_map.keys()) & set(db_map.keys()))
        if not common_dates:
            summary.append((stock_id, None, "无共同日期"))
            continue

        diffs = []
        for d in common_dates:
            tx_p = tx_map[d]
            db_p = db_map[d]
            diff = db_p - tx_p
            diff_pct = (diff / tx_p * 100) if tx_p else 0
            diffs.append((d, tx_p, db_p, diff, diff_pct))

        avg_pct = sum(x[4] for x in diffs) / len(diffs)
        max_diff = max(abs(x[3]) for x in diffs)
        summary.append((stock_id, avg_pct, max_diff, len(common_dates)))

    # 汇总输出
    print("\n" + "=" * 70)
    print("汇总（腾讯QFQ vs DB load_qfq 平均差值%）")
    print("=" * 70)
    print(f"  {'股票':<12} {'平均差值%':>12} {'最大绝对差值':>14} {'天数':>6}  状态")
    print("  " + "-" * 55)

    ok_count = 0
    diff_count = 0
    fail_count = 0

    for item in summary:
        stock_id = item[0]
        if item[1] is None:
            print(f"  {stock_id:<12} {'—':>12} {'—':>14} {'—':>6}  {item[2]}")
            fail_count += 1
        else:
            avg_pct, max_diff, n_days = item[1], item[2], item[3]
            status = "✓ 一致" if abs(avg_pct) < 0.01 else "△ 有差异"
            if abs(avg_pct) < 0.01:
                ok_count += 1
            else:
                diff_count += 1
            print(f"  {stock_id:<12} {avg_pct:>+11.3f}% {max_diff:>14.4f} {n_days:>6}  {status}")

    print("  " + "-" * 55)
    print(f"  一致(差值<0.01%): {ok_count}  有差异: {diff_count}  失败: {fail_count}")
    print("=" * 70)


if __name__ == "__main__":
    main()
