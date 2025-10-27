-- 添加 is_first 字段到 investment_operations 表
ALTER TABLE investment_operations 
ADD COLUMN is_first TINYINT(1) DEFAULT 0 COMMENT '是否首次买入（1=是，0=否）' AFTER note;

-- 标记现有的首次买入记录
UPDATE investment_operations o
INNER JOIN (
    SELECT trade_id, MIN(date) as first_date, MIN(id) as first_id
    FROM investment_operations
    WHERE type IN ('buy', 'add')
    GROUP BY trade_id
) t ON o.trade_id = t.trade_id
SET o.is_first = 1
WHERE o.id = t.first_id;
