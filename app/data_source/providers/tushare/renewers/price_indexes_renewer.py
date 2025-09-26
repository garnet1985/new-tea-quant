"""
价格指数数据更新器
使用基础类简化代码
"""
from app.data_source.providers.tushare.base_renewer import BaseRenewer
from app.data_source.providers.tushare.main_service import TushareService
from app.conf.conf import data_default_start_date
from datetime import datetime
from loguru import logger
from utils.icon.icon_service import IconService


class PriceIndexesRenewer(BaseRenewer):
    """价格指数数据更新器"""
    
    def renew(self, latest_market_open_day: str = None):
        """
        刷新宏观价格/景气度指标（CPI/PPI/PMI/货币供应量M0/M1/M2）到 `price_indexes` 基础表。
        - 主键: ['id', 'date']，此处 id 固定为 'CN'
        - date 取每月第一天，格式 YYYY-MM-01
        数据来源：
        - 货币供应量: cn_m（money supply） [tushare: doc_id=242]
        - CPI: cpi [tushare: doc_id=228]
        - PPI: ppi [tushare: doc_id=245]
        - PMI: pmi [tushare: doc_id=325]
        """
        # 统一起止区间（与K线一致）：若未显式传入，则用配置默认起点 → 最新交易日
        start_m = TushareService.to_yyyymm(data_default_start_date)
        end_m = TushareService.to_yyyymm(latest_market_open_day) or datetime.now().strftime('%Y%m')

        by_month = {}

        # 小工具：调试打印
        def _log_df(name: str, df):
            if not self.is_verbose:
                return
            try:
                cols = list(df.columns) if df is not None else []
                logger.info(f"price_indexes | {name} cols: {cols}")
                if df is not None and not df.empty:
                    logger.info(f"price_indexes | {name} head: {df.head(3).to_dict('records')}")
            except Exception:
                pass

        # 1) Money Supply: cn_m
        try:
            df_m = self.api.cn_m(start_m=start_m, end_m=end_m)
            _log_df('cn_m', df_m)
            if df_m is not None and not df_m.empty:
                for _, r in df_m.iterrows():
                    m = str(r.get('month') or r.get('date') or '')
                    if not m:
                        continue
                    row = by_month.setdefault(m, {})
                    row['M0'] = TushareService.safe_to_float(r.get('m0'))
                    row['M0_yoy'] = TushareService.safe_to_float(r.get('m0_yoy'))
                    row['M0_mom'] = TushareService.safe_to_float(r.get('m0_mom'))
                    row['M1'] = TushareService.safe_to_float(r.get('m1'))
                    row['M1_yoy'] = TushareService.safe_to_float(r.get('m1_yoy'))
                    row['M1_mom'] = TushareService.safe_to_float(r.get('m1_mom'))
                    row['M2'] = TushareService.safe_to_float(r.get('m2'))
                    row['M2_yoy'] = TushareService.safe_to_float(r.get('m2_yoy'))
                    row['M2_mom'] = TushareService.safe_to_float(r.get('m2_mom'))
        except Exception as e:
            logger.error(f"cn_m fetch failed: {e}")

        # 2) CPI: cn_cpi
        try:
            df_cpi = self.api.cn_cpi(start_m=start_m, end_m=end_m)
            _log_df('cpi', df_cpi)
            if df_cpi is not None and not df_cpi.empty:
                for _, r in df_cpi.iterrows():
                    m = str(r.get('month') or r.get('date') or '')
                    if not m:
                        continue
                    row = by_month.setdefault(m, {})
                    row['CPI'] = TushareService.safe_to_float(r.get('nt_val'))
                    row['CPI_yoy'] = TushareService.safe_to_float(r.get('nt_val_yoy'))
                    row['CPI_mom'] = TushareService.safe_to_float(r.get('nt_val_mom'))
        except Exception as e:
            logger.error(f"cpi fetch failed: {e}")

        # 3) PPI: cn_ppi
        try:
            df_ppi = self.api.cn_ppi(start_m=start_m, end_m=end_m)
            _log_df('ppi', df_ppi)
            if df_ppi is not None and not df_ppi.empty:
                for _, r in df_ppi.iterrows():
                    m = str(r.get('month') or r.get('date') or '')
                    if not m:
                        continue
                    row = by_month.setdefault(m, {})
                    row['PPI'] = TushareService.safe_to_float(r.get('nt_val'))
                    row['PPI_yoy'] = TushareService.safe_to_float(r.get('nt_val_yoy'))
                    row['PPI_mom'] = TushareService.safe_to_float(r.get('nt_val_mom'))
        except Exception as e:
            logger.error(f"ppi fetch failed: {e}")

        # 4) PMI: cn_pmi
        try:
            df_pmi = self.api.cn_pmi(start_m=start_m, end_m=end_m)
            _log_df('pmi', df_pmi)
            if df_pmi is not None and not df_pmi.empty:
                for _, r in df_pmi.iterrows():
                    m = str(r.get('month') or r.get('date') or '')
                    if not m:
                        continue
                    row = by_month.setdefault(m, {})
                    row['PMI'] = TushareService.safe_to_float(r.get('nt_val'))
                    row['PMI_yoy'] = TushareService.safe_to_float(r.get('nt_val_yoy'))
                    row['PMI_mom'] = TushareService.safe_to_float(r.get('nt_val_mom'))
        except Exception as e:
            logger.error(f"pmi fetch failed: {e}")

        # 转换为记录格式
        records = []
        for month, data in by_month.items():
            if not month:
                continue
            # 确保月份格式为 YYYY-MM-01
            if len(month) == 6:  # YYYYMM
                month_formatted = f"{month[:4]}-{month[4:6]}-01"
            else:
                month_formatted = month
            
            # 确保所有必填字段都有值
            record = {
                'id': 'CN',
                'date': month_formatted,
                'CPI': data.get('CPI', 0.0),
                'CPI_yoy': data.get('CPI_yoy', 0.0),
                'CPI_mom': data.get('CPI_mom', 0.0),
                'PPI': data.get('PPI', 0.0),
                'PPI_yoy': data.get('PPI_yoy', 0.0),
                'PPI_mom': data.get('PPI_mom', 0.0),
                'PMI': data.get('PMI', 0.0),
                'PMI_l_scale': data.get('PMI_l_scale', 0.0),
                'PMI_m_scale': data.get('PMI_m_scale', 0.0),
                'PMI_s_scale': data.get('PMI_s_scale', 0.0),
                'M0': data.get('M0', 0.0),
                'M0_yoy': data.get('M0_yoy', 0.0),
                'M0_mom': data.get('M0_mom', 0.0),
                'M1': data.get('M1', 0.0),
                'M1_yoy': data.get('M1_yoy', 0.0),
                'M1_mom': data.get('M1_mom', 0.0),
                'M2': data.get('M2', 0.0),
                'M2_yoy': data.get('M2_yoy', 0.0),
                'M2_mom': data.get('M2_mom', 0.0)
            }
            records.append(record)

        if not records:
            logger.info("price_indexes: no records to save")
            return True

        try:
            table = self.db.get_table_instance('price_indexes')
            table.replace(records, ['id', 'date'])
            logger.info(f"{IconService.get('success')} price_indexes 更新完毕")
            return True
        except Exception as e:
            logger.error(f"{IconService.get('error')} price_indexes 更新失败: {e}")
            return False
