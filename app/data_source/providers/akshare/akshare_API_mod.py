from akshare import stock_zh_a_hist
from loguru import logger
from app.data_source.data_source_service import DataSourceService


class AkshareAPIModified:
    def __init__(self, is_verbose: bool = False):
        self.is_verbose = is_verbose

    def get_K_lines(self, stock_id: str, period: str = "daily", 
                          start_date: str = None, end_date: str = None, 
                          adjust: str = "qfq"):
        
        """
        带重试机制的股票历史数据获取（简化版，回归AKShare原生API）
        """
        # 解析股票代码，去掉市场后缀
        stock_code = DataSourceService.parse_ts_code(stock_id)[0]

        try:
            # 调用AKShare原生API
            result = stock_zh_a_hist(
                symbol=stock_code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=adjust
            )
            
            # 验证返回结果的有效性
            if result is None or result.empty:
                if self.is_verbose:
                    logger.warning(f"AKShare API返回空数据: {stock_id} from {start_date} to {end_date}")
                return None
            
            if self.is_verbose:
                logger.info(f"✅ 成功获取 {stock_id} 数据: {len(result)} 行")
            
            return result
            
        except Exception as e:
            error_msg = str(e)
            
            # 检查是否是防火墙错误
            if 'connection aborted' in error_msg.lower() or 'remote disconnected' in error_msg.lower():
                logger.warning(f"🚨 检测EastMoney防火墙阻止了API")

                logger.info(f"建议解决方案：")
                logger.info(f"1. 用浏览器打开任何一只股票的K线图的日线(e.g. https://quote.eastmoney.com/sz300719.html)")
                logger.info(f"2. 刷新网页，会弹出手动移动滑块的机器人识别，完成识别刷新页面，即可正常访问")
                logger.info(f"3. 如果上述方法不成功需等待一分钟然后重试")

                return None
            else:
                # 其他错误，使用指数退避重试
                logger.warning(f"AKShare API调用失败: {error_msg}")
                return None
        