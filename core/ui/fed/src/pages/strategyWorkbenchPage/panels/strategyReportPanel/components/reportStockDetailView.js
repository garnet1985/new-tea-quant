import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Box,
  Button,
  Stack,
  Tab,
  Tabs,
  Typography,
} from '@mui/material';
import ReactECharts from 'echarts-for-react';
import InlineLoadingState from 'components/inlineLoadingState/inlineLoadingState';
import { fetchStrategyStockDetail } from '../../../../../api/apis/strategyApi';
import BacktestPeriodBanner from './backtestPeriodBanner';
import { buildStockKlineChartOptionFromPayload } from '../lib/stockKlineChart';
import {
  buildStockKlineCacheKey,
  findStockKlineCacheByStock,
  getStockKlineMemoryCache,
  setStockKlineMemoryCache,
} from '../lib/stockKlineMemoryCache';
import { STEP_TABS } from '../constants/strategyReportConstants';
import { normalizeEnumMetricsFromSummary } from '../../../reportMetrics/strategyReportMetricsNormalize';
import StockEnumDetailReport from './stockEnumDetailReport';

const DETAIL_LAYER_TABS = STEP_TABS.map((t) => ({ key: t.key, label: t.label }));

function ReportStockDetailView({
  strategyName,
  versionId,
  stock,
  initialStep = 'enum',
  stepStatus = {},
  onBack,
}) {
  const [activeLayer, setActiveLayer] = useState(initialStep);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [payload, setPayload] = useState(null);

  const stockCode = stock?.stockCode || '';
  const stockName = stock?.stockName || stockCode;

  const layerEnabled = useCallback((key) => stepStatus?.[key] === 'done', [stepStatus]);

  const loadDetail = useCallback(async (stepKey) => {
    if (!strategyName || !versionId || !stockCode) return;
    if (!layerEnabled(stepKey)) return;

    setLoading(true);
    setError('');

    try {
      const json = await fetchStrategyStockDetail(strategyName, stepKey, versionId, stockCode);
      const bp = json?.backtest_period || {};
      const params = json?.kline_params || {};
      const cacheKey = buildStockKlineCacheKey({
        strategyName,
        versionId,
        stockId: stockCode,
        term: params.term,
        adjust: params.adjust,
        startDate: bp.start_date,
        endDate: bp.end_date,
      });

      let candles = json?.candles;
      let indicatorSeries = json?.indicator_series;
      let backtestPeriod = bp;
      let klineParams = params;
      const markers = json?.markers;
      let cached = getStockKlineMemoryCache(cacheKey);
      if (!cached?.candles?.length) {
        cached = findStockKlineCacheByStock({
          strategyName,
          versionId,
          stockId: stockCode,
        });
      }
      if (cached && Array.isArray(cached.candles) && cached.candles.length > 0) {
        candles = cached.candles;
        indicatorSeries = cached.indicator_series || indicatorSeries;
        backtestPeriod = cached.backtest_period || backtestPeriod;
        klineParams = cached.kline_params || klineParams;
      } else if (Array.isArray(candles) && candles.length > 0) {
        setStockKlineMemoryCache(cacheKey, {
          candles,
          indicator_series: indicatorSeries,
          backtest_period: bp,
          kline_params: params,
        });
      }

      setPayload({
        ...json,
        backtest_period: backtestPeriod,
        kline_params: klineParams,
        candles: candles || [],
        indicator_series: indicatorSeries || [],
        markers: markers || [],
      });
      if (!json?.detail_available && json?.message && !(candles && candles.length > 0)) {
        setError(json.message);
      }
    } catch (e) {
      setPayload(null);
      setError(e?.message || '加载单股详情失败');
    } finally {
      setLoading(false);
    }
  }, [layerEnabled, stockCode, strategyName, versionId]);

  useEffect(() => {
    if (!layerEnabled(activeLayer)) return;
    loadDetail(activeLayer);
  }, [activeLayer, loadDetail, layerEnabled]);

  const chartOption = useMemo(
    () => buildStockKlineChartOptionFromPayload(payload),
    [payload],
  );

  const periodSlot = useMemo(() => {
    if (!payload?.backtest_period) return null;
    return { backtest_period: payload.backtest_period };
  }, [payload]);

  const enumMetrics = useMemo(() => {
    if (activeLayer !== 'enum' || !payload?.report?.available) return null;
    const raw = payload?.report?.enumMetrics;
    if (!raw || typeof raw !== 'object') return null;
    return normalizeEnumMetricsFromSummary({ enumMetrics: raw });
  }, [activeLayer, payload]);

  const priceAdjustLabel = useMemo(() => {
    const adj = String(payload?.kline_params?.adjust || 'qfq').toLowerCase();
    if (adj === 'qfq') return '前复权 (qfq)';
    if (adj === 'hfq') return '后复权 (hfq)';
    if (adj === 'none' || adj === 'nfq') return '不复权';
    return adj;
  }, [payload]);

  return (
    <Stack spacing={1.25} className="ntq-report-stock-detail">
      <Stack direction="row" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <Button size="small" variant="text" onClick={onBack}>
            ← 返回逐股列表
          </Button>
          <Typography variant="subtitle2" fontWeight={700}>
            {stockCode}
            {stockName && stockName !== stockCode ? ` · ${stockName}` : ''}
          </Typography>
        </Stack>
      </Stack>

      <Tabs
        value={activeLayer}
        onChange={(_e, v) => setActiveLayer(v)}
        variant="scrollable"
        allowScrollButtonsMobile
      >
        {DETAIL_LAYER_TABS.map((tab) => {
          const enabled = layerEnabled(tab.key);
          return (
            <Tab
              key={tab.key}
              value={tab.key}
              label={tab.label}
              disabled={!enabled}
              title={enabled ? '' : '需先完成该步回测'}
            />
          );
        })}
      </Tabs>

      <BacktestPeriodBanner slot={periodSlot} />
      {payload?.candles?.length ? (
        <Typography variant="caption" color="text.secondary">
          K 线：{priceAdjustLabel}
          {payload?.kline_params?.term ? ` · ${payload.kline_params.term}` : ''}
          {payload?.indicator_series?.length
            ? ` · 副图：${payload.indicator_series.map((s) => s.label || s.key).join('、')}`
            : ''}
        </Typography>
      ) : null}

      {loading ? (
        <InlineLoadingState block message="正在加载 K 线与标注…" />
      ) : (
        <>
          {error ? (
            <Typography variant="body2" color="error">{error}</Typography>
          ) : null}
          <Box sx={{ height: 560, width: '100%' }}>
            {Object.keys(chartOption).length > 0 ? (
              <ReactECharts
                option={chartOption}
                style={{ height: '100%', width: '100%' }}
                notMerge
                lazyUpdate
              />
            ) : (
              <Typography variant="body2" color="text.secondary">
                暂无 K 线数据
              </Typography>
            )}
          </Box>
          {Object.keys(chartOption).length > 0 ? (
            <Typography variant="caption" color="text.secondary">
              使用底部滑块调整可见区间
            </Typography>
          ) : null}
        </>
      )}

      {activeLayer === 'enum' ? (
        <StockEnumDetailReport metrics={enumMetrics} />
      ) : (
        <Box className="ntq-report-stock-detail__report-placeholder">
          <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 0.5 }}>
            单股报告
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {payload?.report?.message || '该步骤单股报告尚未开放'}
          </Typography>
        </Box>
      )}
    </Stack>
  );
}

export default ReportStockDetailView;
