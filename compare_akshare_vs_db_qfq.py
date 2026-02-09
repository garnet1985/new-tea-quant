#!/usr/bin/env python3
"""
对比 AKShare 前复权价格 vs DB load_qfq 价格

注意：AKShare 的 stock_zh_a_hist 数据来源也是东方财富，本质与直接调东方财富 API 相同。

用途：先验证 AKShare 能否正常拉取数据，以及和 DB 中已有数据的一致性。
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def fetch_akshare_qfq(stock_id: str, start_date: str, end_date: str) -> dict:
    """
    从 AKShare 获取前复权收盘价，返回 {date_ymd: close}
    
    stock_id: 000001.SZ 或 600000.SH
    start_date/end_date: YYYYMMDD
    """
    try:
        import akshare as ak
    except ImportError:
        print("  AKShare: 未安装，请 pip install akshare")
        return {}
    
    # AKShare 需要 6 位纯数字
    symbol = stock_id.split(".")[0] if "." in stock_id else stock_id
    
    try:
        df = ak.stock_zh_a_hist(
            symbol=symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust="qfq",
        )
    except Exception as e:
        print(f"  AKShare: 拉取失败 {e}")
        return {}
    
    if df is None or df.empty:
        return {}
    
    result = {}
    date_col = "日期" if "日期" in df.columns else "date"
    close_col = "收盘" if "收盘" in df.columns else "close"
    if date_col not in df.columns or close_col not in df.columns:
        print(f"  AKShare: 列名异常 {list(df.columns)}")
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
    stocks = ["000001.SZ", "600000.SH", "000002.SZ"]  # 平安银行、浦发银行、万科A
    start_ymd = "20240102"
    end_ymd = "20240131"

    print("=" * 70)
    print("AKShare 前复权 vs DB load_qfq 价格对比")
    print("=" * 70)
    print("说明：AKShare stock_zh_a_hist 数据来源 = 东方财富")
    print(f"股票: {stocks}")
    print(f"时间段: {start_ymd} ~ {end_ymd}")
    print()

    # 初始化 DataManager
    from core.modules.data_manager import DataManager

    data_mgr = DataManager(is_verbose=False)
    data_mgr.initialize()

    for stock_id in stocks:
        print(f"\n--- {stock_id} ---")

        # AKShare
        akshare_map = fetch_akshare_qfq(stock_id, start_ymd, end_ymd)
        if not akshare_map:
            print(f"  AKShare: 无数据")
            continue
        print(f"  AKShare: {len(akshare_map)} 条")

        # DB load_qfq
        try:
            db_klines = data_mgr.stock.kline.load_qfq(
                stock_id, term="daily", start_date=start_ymd, end_date=end_ymd
            )
        except Exception as e:
            print(f"  DB load_qfq: 错误 {e}")
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
            print(f"  DB load_qfq: 无数据")
            continue
        print(f"  DB load_qfq: {len(db_map)} 条")

        # 对比共同日期
        common_dates = sorted(set(akshare_map.keys()) & set(db_map.keys()))
        if not common_dates:
            print(f"  共同日期: 0")
            continue

        diffs = []
        for d in common_dates:
            ak_p = akshare_map[d]
            db_p = db_map[d]
            diff = db_p - ak_p
            diff_pct = (diff / ak_p * 100) if ak_p else 0
            diffs.append((d, ak_p, db_p, diff, diff_pct))

        # 输出前 5 条 + 统计
        print(f"  共同日期: {len(common_dates)} 天")
        print(f"  {'日期':<10} {'AKShare':>10} {'DB':>10} {'差值':>10} {'差值%':>8}")
        print("  " + "-" * 52)
        for d, ak_p, db_p, diff, pct in diffs[:5]:
            print(f"  {d}  {ak_p:>10.4f} {db_p:>10.4f} {diff:>+10.4f} {pct:>+7.3f}%")
        if len(diffs) > 5:
            print("  ...")
        avg_diff = sum(x[3] for x in diffs) / len(diffs)
        max_diff = max(abs(x[3]) for x in diffs)
        avg_pct = sum(x[4] for x in diffs) / len(diffs)
        print(f"  平均差值: {avg_diff:+.4f}, 最大绝对差值: {max_diff:.4f}, 平均差值%: {avg_pct:+.3f}%")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
