from datetime import date as date_type

class DataSourceService:
    @staticmethod
    def parse_ts_code(ts_code: str):
        code, market = ts_code.split('.', 1)
        return code, market

    @staticmethod
    def to_hyphen_date(date: str):
        # 20250804 -> 2025-08-04
        return f"{date[:4]}-{date[4:6]}-{date[6:]}"
    
    @staticmethod
    def to_hyphen_date_type(date: str):
        return date_type(int(date[:4]), int(date[4:6]), int(date[6:8]))

    @staticmethod
    def to_str_date(date: str):
        # 2025-08-04 -> 20250804
        return date.replace('-', '')

    @staticmethod
    def to_qfq(k_lines: list, qfq_factors: list):
        """
        计算前复权价格
        
        Args:
            k_lines: K线数据列表，包含 date, open, close, highest, lowest 等字段
            qfq_factors: 复权因子列表，包含 date, qfq 等字段
            
        Returns:
            list: 前复权后的K线数据列表
        """
        if not k_lines or not qfq_factors:
            return k_lines
            
        # 确保因子按日期升序
        sorted_factors = sorted(qfq_factors, key=lambda x: x['date'])
        
        # 获取第一个（最早的）复权因子作为默认值
        default_factor = sorted_factors[0]['qfq'] if sorted_factors else 1.0
        
        # 处理每条K线
        for k_line in k_lines:
            # 保存原始值到raw属性
            k_line['raw'] = {
                'open': k_line.get('open'),
                'close': k_line.get('close'),
                'highest': k_line.get('highest'),
                'lowest': k_line.get('lowest')
            }
            
            # 获取当前K线的日期
            current_date = k_line.get('date')
            if not current_date:
                continue
                
            # 查找对应的复权因子
            qfq_factor = DataSourceService._find_qfq_factor(current_date, sorted_factors)
            
            # 如果没有找到复权因子，使用默认因子
            if qfq_factor is None:
                qfq_factor = default_factor
                print(f"日期 {current_date} 使用默认复权因子: {default_factor}")
            
            if qfq_factor is not None:
                # 计算前复权价格
                k_line['open'] = k_line['raw']['open'] * qfq_factor if k_line['raw']['open'] else None
                k_line['close'] = k_line['raw']['close'] * qfq_factor if k_line['raw']['close'] else None
                k_line['highest'] = k_line['raw']['highest'] * qfq_factor if k_line['raw']['highest'] else None
                k_line['lowest'] = k_line['raw']['lowest'] * qfq_factor if k_line['raw']['lowest'] else None
            else:
                # 保持原值
                pass
        
        return k_lines
    
    @staticmethod
    def _find_qfq_factor(target_date: str, sorted_factors: list) -> float:
        """
        查找目标日期对应的复权因子
        
        算法：找到目标日期所在的时间段，返回该时间段的复权因子
        时间段定义：大于等于前一个因子日期，小于后一个因子日期
        
        Args:
            target_date: 目标日期 (YYYYMMDD格式)
            sorted_factors: 按时间升序排列的复权因子列表
            
        Returns:
            float: 复权因子，如果没找到返回None
        """
        if not sorted_factors:
            return None
            
        # 如果只有一个因子，直接返回
        if len(sorted_factors) == 1:
            return sorted_factors[0]['qfq']
        
        # 找到目标日期对应的复权因子
        # 规则：使用小于等于目标日期的最近一个复权因子
        result_factor = None
        
        for factor in sorted_factors:
            factor_date = factor['date']
            if target_date >= factor_date:
                result_factor = factor['qfq']
            else:
                # 如果目标日期小于因子日期，说明已经超过了，使用上一个因子
                break
        
        return result_factor

    