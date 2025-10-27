-- 添加 updated_at 字段到 investment_operations 表
ALTER TABLE investment_operations 
ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间' AFTER created_at;

-- 更新现有记录的created_at（使用date字段作为created_at）
UPDATE investment_operations 
SET created_at = CONCAT(date, ' 00:00:00')
WHERE created_at IS NULL;
