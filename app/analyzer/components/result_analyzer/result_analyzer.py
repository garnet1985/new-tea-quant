from typing import Any, Dict, List
from loguru import logger
from utils.date.date_utils import DateUtils
from utils.icon.icon_service import IconService


class ResultAnalyzer:
    def __init__(self):
        from app.analyzer.components.investment.investment_recorder import InvestmentRecorder
        self.investment_recorder = InvestmentRecorder()

    # ==================================================
    # Market period definitions (migrated from BaseStrategy)
    # ==================================================
    MARKET_PERIODS = [
        ("20080101", "20081031", "bear"),
        ("20081101", "20090731", "bull"),
        ("20090801", "20140630", "stable"),
        ("20140701", "20150630", "bull"),
        ("20150701", "20190131", "bear"),
        ("20190201", "20210228", "bull"),
        ("20210301", "20221031", "stable"),
        ("20221101", "20230430", "bull"),
        ("20230501", "20240131", "bear"),
        ("20240201", "20250930", "stable"),
    ]

    # ==================================================
    # Utilities (migrated from BaseStrategy)
    # ==================================================
    def _get_market_type(self, date_str: str) -> str:
        date_num = int(date_str[:8]) if date_str else 0
        for start_date, end_date, market_type in self.MARKET_PERIODS:
            start_num = int(start_date)
            end_num = int(end_date)
            if start_num <= date_num <= end_num:
                return market_type
        return "unknown"

    def _parse_date_for_grouping(self, date_str: str) -> tuple:
        if date_str and len(date_str) >= 8:
            year = date_str[:4]
            month = date_str[4:6]
            return year, month
        return None, None

    def _group_by_time_period(self, data_list: List[Dict[str, Any]], date_field: str) -> Dict[str, Any]:
        by_year: Dict[str, List[Dict[str, Any]]] = {}
        by_month: Dict[str, List[Dict[str, Any]]] = {}
        for item in data_list or []:
            date_str = item.get(date_field, "")
            if not date_str:
                continue
            year, month = self._parse_date_for_grouping(date_str)
            if not year or not month:
                continue
            year_key = year
            month_key = f"{year}-{month}"
            by_year.setdefault(year_key, []).append(item)
            by_month.setdefault(month_key, []).append(item)
        return {"by_year": by_year, "by_month": by_month}

    # ==================================================
    # Distributions and performance (migrated)
    # ==================================================
    def get_opportunity_distribution(self, opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self._group_by_time_period(opportunities, "date")

    def get_performance_in_every_period(self, investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self._group_by_time_period(investments, "invest_date")

    def get_successful_investment_distribution(self, investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        successful_investments = [inv for inv in investments if inv.get("roi", 0) > 0]
        return self._group_by_time_period(successful_investments, "invest_date")

    def get_failed_investment_distribution(self, investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        failed_investments = [inv for inv in investments if inv.get("roi", 0) <= 0]
        return self._group_by_time_period(failed_investments, "invest_date")

    def _get_performance_by_market_type(self, investments: List[Dict[str, Any]], market_type: str) -> Dict[str, Any]:
        filtered_investments: List[Dict[str, Any]] = []
        for inv in investments or []:
            invest_date = inv.get("invest_date", "")
            if invest_date and self._get_market_type(invest_date) == market_type:
                filtered_investments.append(inv)
        if not filtered_investments:
            return {
                "total_investments": 0,
                "successful_investments": 0,
                "failed_investments": 0,
                "win_rate": 0.0,
                "avg_roi": 0.0,
                "total_roi": 0.0,
                "investments": [],
            }
        total_investments = len(filtered_investments)
        successful_investments = len([inv for inv in filtered_investments if inv.get("roi", 0) > 0])
        failed_investments = total_investments - successful_investments
        win_rate = (successful_investments / total_investments * 100) if total_investments > 0 else 0.0
        total_roi = sum(inv.get("roi", 0) for inv in filtered_investments)
        avg_roi = total_roi / total_investments if total_investments > 0 else 0.0
        return {
            "total_investments": total_investments,
            "successful_investments": successful_investments,
            "failed_investments": failed_investments,
            "win_rate": win_rate,
            "avg_roi": avg_roi,
            "total_roi": total_roi,
            "investments": filtered_investments,
        }

    def get_strategy_performance_in_uptrend_market(self, investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self._get_performance_by_market_type(investments, "bull")

    def get_strategy_performance_in_downtrend_market(self, investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self._get_performance_by_market_type(investments, "bear")

    def get_strategy_performance_in_stable_market(self, investments: List[Dict[str, Any]]) -> Dict[str, Any]:
        return self._get_performance_by_market_type(investments, "stable")

    # ==================================================
    # Extractors (migrated)
    # ==================================================
    def _extract_investments_from_simulation_results(self, simulation_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        investments: List[Dict[str, Any]] = []
        stocks = simulation_results.get("stocks", [])
        for stock_data in stocks:
            stock_id = stock_data.get("stock", {}).get("id", "") or stock_data.get("stock_info", {}).get("id", "")
            summary = stock_data.get("summary", {})
            total_investments = summary.get("total_investments", 0)
            avg_roi = summary.get("avg_roi", 0)
            if "investments" in stock_data:
                for inv in stock_data["investments"]:
                    investments.append({
                        "stock_id": stock_id,
                        "invest_date": inv.get("start_date", "") or inv.get("invest_date", ""),
                        "sell_date": inv.get("end_date", "") or inv.get("sell_date", ""),
                        "roi": inv.get("overall_profit_rate", 0) * 100 if inv.get("overall_profit_rate") is not None else inv.get("roi", 0),
                        "duration_days": inv.get("duration_in_days", 0) or inv.get("duration_days", 0),
                    })
            else:
                if total_investments > 0:
                    investments.append({
                        "stock_id": stock_id,
                        "invest_date": "unknown",
                        "sell_date": "unknown",
                        "roi": avg_roi,
                        "duration_days": summary.get("avg_duration_days", 0),
                    })
        return investments

    def _extract_opportunities_from_simulation_results(self, simulation_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        opportunities: List[Dict[str, Any]] = []
        stocks = simulation_results.get("stocks", [])
        for stock_data in stocks:
            stock_id = stock_data.get("stock", {}).get("id", "") or stock_data.get("stock_info", {}).get("id", "")
            if "investments" in stock_data:
                for inv in stock_data["investments"]:
                    opportunities.append({
                        "stock_id": stock_id,
                        "date": inv.get("start_date", "") or inv.get("invest_date", ""),
                        "roi": inv.get("overall_profit_rate", 0) * 100 if inv.get("overall_profit_rate") is not None else inv.get("roi", 0),
                    })
            else:
                summary = stock_data.get("summary", {})
                total_investments = summary.get("total_investments", 0)
                if total_investments > 0:
                    opportunities.append({
                        "stock_id": stock_id,
                        "date": "unknown",
                        "roi": summary.get("avg_roi", 0),
                    })
        return opportunities

    # ==================================================
    # Public APIs
    # ==================================================
    def analyze_simulation_results(self, simulation_results: Dict[str, Any]) -> Dict[str, Any]:
        investments = self._extract_investments_from_simulation_results(simulation_results)
        opportunities = self._extract_opportunities_from_simulation_results(simulation_results)
        analysis = {
            "session_summary": simulation_results.get("session", {}),
            "opportunity_distribution": self.get_opportunity_distribution(opportunities),
            "performance_in_every_period": self.get_performance_in_every_period(investments),
            "successful_investment_distribution": self.get_successful_investment_distribution(investments),
            "failed_investment_distribution": self.get_failed_investment_distribution(investments),
            "bull_market_performance": self.get_strategy_performance_in_uptrend_market(investments),
            "bear_market_performance": self.get_strategy_performance_in_downtrend_market(investments),
            "stable_market_performance": self.get_strategy_performance_in_stable_market(investments),
        }
        return analysis

    def get_base_analysis(self, strategy_folder_name: str = "HL", session_id: str = None) -> Dict[str, Any]:
        try:
            self.investment_recorder.set_strategy_folder_name(strategy_folder_name)
            simulation_results = self.investment_recorder.get_simulation_results(session_id)
            if not simulation_results.get("session") or not simulation_results.get("stocks"):
                logger.warning(f"策略 {strategy_folder_name} 没有找到模拟结果数据")
                return {
                    "error": "No simulation data found",
                    "strategy": strategy_folder_name,
                    "session_id": session_id,
                }
            analysis = self.analyze_simulation_results(simulation_results)
            analysis["strategy_info"] = {
                "strategy_name": strategy_folder_name,
                "session_id": session_id or self.investment_recorder.get_latest_session_id(),
                "analysis_time": DateUtils.get_current_date_str(DateUtils.DATE_FORMAT_YYYY_MM_DD_HH_MM_SS),
                "total_stocks": len(simulation_results.get("stocks", [])),
            }
            logger.info(f"✅ 成功生成策略 {strategy_folder_name} 的基础分析报告")
            return analysis
        except Exception as e:
            logger.error(f"❌ 生成策略 {strategy_folder_name} 基础分析报告失败: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e), "strategy": strategy_folder_name, "session_id": session_id}

    def print_analysis_results(self, analysis: Dict[str, Any]) -> None:
        print(f"\n{'='*60}")
        print(f"📊 策略分析报告")
        print(f"{'='*60}")
        strategy_info = analysis.get("strategy_info", {})
        print(f"策略名称: {strategy_info.get('strategy_name', 'Unknown')}")
        print(f"会话ID: {strategy_info.get('session_id', 'Unknown')}")
        print(f"分析时间: {strategy_info.get('analysis_time', 'Unknown')}")
        print(f"股票数量: {strategy_info.get('total_stocks', 0)}")
        session = analysis.get("session_summary", {})
        print(f"\n📈 整体表现:")
        print(f"  总投资次数: {session.get('total_investments', 0)}")
        print(f"  当前投资次数: {session.get('total_open_investments', 0)}")
        print(f"  总股票数: {session.get('stocks_have_opportunities', 0)}")
        print(f"  有投资的股票数: {session.get('stocks_have_opportunities', 0)}")
        print(f"  胜率: {session.get('win_rate', 0):.1f}%")
        avg_roi = session.get("avg_roi", 0)
        avg_roi_percent = avg_roi * 100
        print(f"  平均ROI: {avg_roi_percent:.2f}%")
        annual_return = session.get("annual_return", 0)
        print(f"  平均年化收益: {annual_return:.2f}%")
        print(f"  平均持有时长: {session.get('avg_duration_in_days', 0):.0f}天")
        bull_perf = analysis["bull_market_performance"]
        bear_perf = analysis["bear_market_performance"]
        stable_perf = analysis["stable_market_performance"]
        print(f"\n🎯 各市场表现:")
        print(f"  🐂 牛市: 投资{bull_perf['total_investments']}次, 胜率{bull_perf['win_rate']:.1f}%, 平均ROI {bull_perf['avg_roi']:.2f}%")
        print(f"  🐻 熊市: 投资{bear_perf['total_investments']}次, 胜率{bear_perf['win_rate']:.1f}%, 平均ROI {bear_perf['avg_roi']:.2f}%")
        print(f"  📈 震荡市: 投资{stable_perf['total_investments']}次, 胜率{stable_perf['win_rate']:.1f}%, 平均ROI {stable_perf['avg_roi']:.2f}%")
        opp_dist = analysis["opportunity_distribution"]
        perf_dist = analysis["performance_in_every_period"]
        success_dist = analysis["successful_investment_distribution"]
        failed_dist = analysis["failed_investment_distribution"]
        print(f"\n📅 投资分布分析:")
        print(f"  按年份分布:")
        if opp_dist["by_year"]:
            total_opportunities = sum(len(opps) for opps in opp_dist["by_year"].values())
            total_investments = sum(len(invs) for invs in perf_dist["by_year"].values())
            total_success = sum(len(invs) for invs in success_dist["by_year"].values())
            total_failed = sum(len(invs) for invs in failed_dist["by_year"].values())
            for year in sorted(opp_dist["by_year"].keys()):
                opps = opp_dist["by_year"].get(year, [])
                opp_count = len(opps)
                opp_percentage = (opp_count / total_opportunities * 100) if total_opportunities > 0 else 0
                invs = perf_dist["by_year"].get(year, [])
                inv_count = len(invs)
                avg_roi_year = sum(inv.get("roi", 0) for inv in invs) / len(invs) if invs else 0
                success_invs = success_dist["by_year"].get(year, [])
                success_count = len(success_invs)
                success_percentage = (success_count / total_success * 100) if total_success > 0 else 0
                success_rate_in_year = (success_count / inv_count * 100) if inv_count > 0 else 0
                failed_invs = failed_dist["by_year"].get(year, [])
                failed_count = len(failed_invs)
                failed_percentage = (failed_count / total_failed * 100) if total_failed > 0 else 0
                failed_rate_in_year = (failed_count / inv_count * 100) if inv_count > 0 else 0
                print(f"\n    {year}年: {opp_count}个机会 (总占比{opp_percentage:.1f}%) - 平均ROI {avg_roi_year:.2f}% 其中:")
                print(f"      - {IconService.get('success')}成功投资: {success_count}次 占比{success_rate_in_year:.1f}% | (总占比{success_percentage:.1f}%)")
                print(f"      - {IconService.get('failed')}失败投资: {failed_count}次 占比{failed_rate_in_year:.1f}% | (总占比{failed_percentage:.1f}%)")
        print(f"\n  按月份分布 (1-12月):")
        if opp_dist["by_month"]:
            month_opp_stats: Dict[str, int] = {}
            month_success_stats: Dict[str, int] = {}
            month_failed_stats: Dict[str, int] = {}
            month_roi_stats: Dict[str, List[Dict[str, Any]]] = {}
            for month_key, opps in opp_dist["by_month"].items():
                if "-" in month_key:
                    month = month_key.split("-")[1]
                    month_opp_stats[month] = month_opp_stats.get(month, 0) + len(opps)
            for month_key, invs in success_dist["by_month"].items():
                if "-" in month_key:
                    month = month_key.split("-")[1]
                    month_success_stats[month] = month_success_stats.get(month, 0) + len(invs)
            for month_key, invs in failed_dist["by_month"].items():
                if "-" in month_key:
                    month = month_key.split("-")[1]
                    month_failed_stats[month] = month_failed_stats.get(month, 0) + len(invs)
            for month_key, invs in perf_dist["by_month"].items():
                if "-" in month_key:
                    month = month_key.split("-")[1]
                    month_roi_stats.setdefault(month, []).extend(invs)
            total_month_opp = sum(month_opp_stats.values())
            total_month_success = sum(month_success_stats.values())
            total_month_failed = sum(month_failed_stats.values())
            for month in ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]:
                opp_count = month_opp_stats.get(month, 0)
                opp_percentage = (opp_count / total_month_opp * 100) if total_month_opp > 0 else 0
                success_count = month_success_stats.get(month, 0)
                success_percentage = (success_count / total_month_success * 100) if total_month_success > 0 else 0
                failed_count = month_failed_stats.get(month, 0)
                failed_percentage = (failed_count / total_month_failed * 100) if total_month_failed > 0 else 0
                month_total_inv = success_count + failed_count
                success_rate_in_month = (success_count / month_total_inv * 100) if month_total_inv > 0 else 0
                failed_rate_in_month = (failed_count / month_total_inv * 100) if month_total_inv > 0 else 0
                month_invs = month_roi_stats.get(month, [])
                avg_roi_month = sum(inv.get("roi", 0) for inv in month_invs) / len(month_invs) if month_invs else 0
                print(f"\n    {month}月: {opp_count}个机会 (总占比{opp_percentage:.1f}%) - 平均ROI {avg_roi_month:.2f}% 其中:")
                print(f"      - {IconService.get('success')} 成功投资: {success_count}次 占比{success_rate_in_month:.1f}% | (总占比{success_percentage:.1f}%)")
                print(f"      - {IconService.get('failed')} 失败投资: {failed_count}次 占比{failed_rate_in_month:.1f}% | (总占比{failed_percentage:.1f}%)")
        print(f"\n{'='*60}")
        print(f"✅ 策略分析完成")
        print(f"{'='*60}")
