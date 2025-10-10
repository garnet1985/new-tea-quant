-- 数据库迁移脚本: camelCase → snake_case (剩余表)
-- 表: lpr, price_indexes, stock_index, stock_index_indicator
-- 生成时间: 2025-10-10 13:42:26.241851

-- ============================================
-- 表: lpr
-- ============================================

ALTER TABLE `lpr` CHANGE COLUMN `LPR_1Y` `lpr_1_y` FLOAT NOT NULL;
ALTER TABLE `lpr` CHANGE COLUMN `LPR_5Y` `lpr_5_y` FLOAT;

-- ============================================
-- 表: price_indexes
-- ============================================

ALTER TABLE `price_indexes` CHANGE COLUMN `CPI` `cpi` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `CPI_yoy` `cpi_yoy` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `CPI_mom` `cpi_mom` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `PPI` `ppi` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `PPI_yoy` `ppi_yoy` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `PPI_mom` `ppi_mom` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `PMI` `pmi` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `PMI_l_scale` `pmi_l_scale` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `PMI_m_scale` `pmi_m_scale` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `PMI_s_scale` `pmi_s_scale` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `M0` `m0` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `M0_yoy` `m0_yoy` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `M0_mom` `m0_mom` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `M1` `m1` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `M1_yoy` `m1_yoy` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `M1_mom` `m1_mom` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `M2` `m2` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `M2_yoy` `m2_yoy` FLOAT NOT NULL;
ALTER TABLE `price_indexes` CHANGE COLUMN `M2_mom` `m2_mom` FLOAT NOT NULL;

-- ============================================
-- 表: stock_index
-- ============================================

ALTER TABLE `stock_index` CHANGE COLUMN `exchangeCenter` `exchange_center` VARCHAR(16) NOT NULL;
ALTER TABLE `stock_index` CHANGE COLUMN `isAlive` `is_alive` TINYINT NOT NULL;
ALTER TABLE `stock_index` CHANGE COLUMN `lastUpdate` `last_update` DATETIME NOT NULL;

-- ============================================
-- 表: stock_index_indicator
-- ============================================

ALTER TABLE `stock_index_indicator` CHANGE COLUMN `priceChangeDelta` `price_change_delta` FLOAT;
ALTER TABLE `stock_index_indicator` CHANGE COLUMN `priceChangeRateDelta` `price_change_rate_delta` FLOAT;
ALTER TABLE `stock_index_indicator` CHANGE COLUMN `preClose` `pre_close` FLOAT;

