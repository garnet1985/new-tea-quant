#!/usr/bin/env python3
"""测试 Baostock API - 前复权 K 线数据"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_baostock():
    try:
        import baostock as bs
    except ImportError:
        print("❌ 未安装 baostock，请先执行: pip install baostock")
        return

    print("测试 Baostock 前复权 K 线 API (000001 平安银行)...")
    print("-" * 60)

    try:
        # 登录
        lg = bs.login()
        if lg.error_code != "0":
            print(f"❌ 登录失败: {lg.error_msg}")
            return
        print("✅ 登录成功")

        # 查询前复权日 K 线
        rs = bs.query_history_k_data_plus(
            "sz.000001",  # 平安银行（深市）
            "date,open,high,low,close,volume",
            start_date="2024-01-01",
            end_date="2024-02-01",
            frequency="d",
            adjustflag="2",  # 2=前复权
        )

        if rs.error_code != "0":
            print(f"❌ 查询失败: {rs.error_msg}")
            bs.logout()
            return

        # 获取数据
        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())

        bs.logout()

        if not data_list:
            print("⚠️ 返回数据为空")
            return

        print(f"✅ 成功! 返回 {len(data_list)} 条前复权记录")
        print(f"\n字段: {rs.fields}")
        print(f"\n前 5 条数据:")
        for row in data_list[:5]:
            print(f"  {row}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_baostock()
