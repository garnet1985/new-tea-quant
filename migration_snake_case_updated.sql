-- 数据库迁移脚本: camelCase → snake_case
-- 表: stock_kline, stock_list
-- 生成时间: 2025-10-10 (updated)
-- 只迁移仍然是 camelCase 的字段

-- ============================================
-- 表: stock_kline
-- ============================================

-- price_change_delta 已经是 snake_case，跳过
ALTER TABLE `stock_kline` CHANGE COLUMN `priceChangeRateDelta` `price_change_rate_delta` FLOAT NOT NULL;
ALTER TABLE `stock_kline` CHANGE COLUMN `preClose` `pre_close` FLOAT NOT NULL;
ALTER TABLE `stock_kline` CHANGE COLUMN `turnoverRate` `turnover_rate` FLOAT NOT NULL;
ALTER TABLE `stock_kline` CHANGE COLUMN `freeTurnoverRate` `free_turnover_rate` FLOAT NOT NULL;
ALTER TABLE `stock_kline` CHANGE COLUMN `volumeRatio` `volume_ratio` FLOAT NOT NULL;
ALTER TABLE `stock_kline` CHANGE COLUMN `peTTM` `pe_ttm` FLOAT NOT NULL;
ALTER TABLE `stock_kline` CHANGE COLUMN `psTTM` `ps_ttm` FLOAT NOT NULL;
ALTER TABLE `stock_kline` CHANGE COLUMN `dvRatio` `dv_ratio` FLOAT NOT NULL;
ALTER TABLE `stock_kline` CHANGE COLUMN `dvTTM` `dv_ttm` FLOAT NOT NULL;
ALTER TABLE `stock_kline` CHANGE COLUMN `totalShare` `total_share` BIGINT NOT NULL;
ALTER TABLE `stock_kline` CHANGE COLUMN `floatShare` `float_share` BIGINT NOT NULL;
ALTER TABLE `stock_kline` CHANGE COLUMN `freeShare` `free_share` BIGINT NOT NULL;
ALTER TABLE `stock_kline` CHANGE COLUMN `totalMarketValue` `total_market_value` FLOAT NOT NULL;
ALTER TABLE `stock_kline` CHANGE COLUMN `circMarketValue` `circ_market_value` FLOAT NOT NULL;

-- ============================================
-- 表: stock_list
-- ============================================

ALTER TABLE `stock_list` CHANGE COLUMN `exchangeCenter` `exchange_center` VARCHAR(16) NOT NULL;
ALTER TABLE `stock_list` CHANGE COLUMN `isActive` `is_active` TINYINT NOT NULL;
ALTER TABLE `stock_list` CHANGE COLUMN `lastUpdate` `last_update` DATETIME NOT NULL;

