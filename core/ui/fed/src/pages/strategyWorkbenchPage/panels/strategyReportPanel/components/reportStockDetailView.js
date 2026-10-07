import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Box,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Typography,
} from '@mui/material';
import ReactECharts from 'echarts-for-react';
import InlineLoadingState from 'views/inlineLoadingState';
import NtqIcon from 'views/ntqIcon';
import { fetchStrategyStockDetail } from '../../../../../api/strategyApi';
import BacktestPeriodBanner from './backtestPeriodBanner';
import {
  buildMarketChartOptionFromStockPayload,
  FinancePitCard,
  pickFinanceSnapshot,
  resolveAxisPointerDate,
  stockKlinePayloadToMarketChartModel,
} from 'containers/marketChart';
import {
  buildStockKlineCacheKey,
  findStockKlineCacheByStock,
  getStockKlineMemoryCache,
  setStockKlineMemoryCache,
} from '../lib/stockKlineMemoryCache';
import { normalizeEnumMetricsFromSummary } from '../../../reportMetrics/strategyReportMetricsNormalize';
import StockEnumDetailReport from './stockEnumDetailReport';

/**
 * 逐股 K 线审阅：全屏弹窗，尽量占满视口以便看清主图 / 附图。
 */
function ReportStockDetailView({
  open,
  strategyName,
  versionId,
  stock,
  initialStep = 'enum',
  stepStatus = {},
  onClose,
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [payload, setPayload] = useState(null);
  /** 财报 PIT：仅十字线悬停时填数；未悬停方块常驻显示 — */
  const [pointerAsOf, setPointerAsOf] = useState('');
  const zoomEndDateRef = useRef('');
  const chartRef = useRef(null);
  const payloadRef = useRef(null);
  const hoverGoalLevelsRef = useRef(null);
  const highlightGroupIdRef = useRef(null);
  const syncRafRef = useRef(null);
  const clearHighlightTimerRef = useRef(null);

  const stockCode = stock?.stockCode || '';
  const stockName = stock?.stockName || stockCode;
  const activeLayer = initialStep;

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
        startDate: bp.start_date,
        endDate: bp.end_date,
      });

      let candles = json?.candles;
      let indicatorSeries = json?.indicator_series;
      let backtestPeriod = bp;
      let klineParams = params;
      const markers = json?.markers;
      const apiHasIndicators = Array.isArray(json?.indicator_series)
        && json.indicator_series.length > 0;
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
        // 指标配置常变：优先用接口最新 series，避免缓存里旧 bbands 等盖住新指标
        if (!apiHasIndicators) {
          indicatorSeries = cached.indicator_series || indicatorSeries;
        }
        backtestPeriod = cached.backtest_period || backtestPeriod;
        klineParams = cached.kline_params || klineParams;
        if (apiHasIndicators) {
          setStockKlineMemoryCache(cacheKey, {
            candles,
            indicator_series: indicatorSeries,
            backtest_period: backtestPeriod,
            kline_params: klineParams,
          });
        }
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
    if (!open) return;
    if (!layerEnabled(activeLayer)) return;
    loadDetail(activeLayer);
  }, [open, activeLayer, loadDetail, layerEnabled]);

  useEffect(() => {
    if (!open) {
      setPayload(null);
      setPointerAsOf('');
      hoverGoalLevelsRef.current = null;
      highlightGroupIdRef.current = null;
      if (clearHighlightTimerRef.current) {
        clearTimeout(clearHighlightTimerRef.current);
        clearHighlightTimerRef.current = null;
      }
    }
  }, [open]);

  useEffect(() => {
    setPointerAsOf('');
    hoverGoalLevelsRef.current = null;
    highlightGroupIdRef.current = null;
    if (clearHighlightTimerRef.current) {
      clearTimeout(clearHighlightTimerRef.current);
      clearHighlightTimerRef.current = null;
    }
    const dates = (payload?.candles || [])
      .map((c) => String(c?.date || '').trim())
      .filter(Boolean);
    zoomEndDateRef.current = dates.length ? dates[dates.length - 1] : '';
  }, [payload]);

  useEffect(() => {
    payloadRef.current = payload;
  }, [payload]);

  useEffect(() => () => {
    if (syncRafRef.current != null) cancelAnimationFrame(syncRafRef.current);
    if (clearHighlightTimerRef.current) clearTimeout(clearHighlightTimerRef.current);
  }, []);

  const buyLevelsByDate = useMemo(() => {
    const map = new Map();
    (payload?.markers || []).forEach((m) => {
      if (String(m?.type || '') !== 'buy') return;
      const date = String(m?.date || '').trim();
      const levels = m?.detail?.planned_levels;
      if (!date || !Array.isArray(levels) || !levels.length) return;
      map.set(date, levels);
    });
    return map;
  }, [payload]);

  // 基础 option 只跟 payload；hover 叠加用 setOption 合并，避免 mousemove 中 notMerge 拆 series
  const chartOption = useMemo(
    () => buildMarketChartOptionFromStockPayload(payload),
    [payload],
  );

  const syncHoverOverlay = useCallback(() => {
    const instance = chartRef.current?.getEchartsInstance?.();
    if (!instance || instance.isDisposed?.() || !payloadRef.current) return;
    const nextOption = buildMarketChartOptionFromStockPayload({
      ...payloadRef.current,
      hoverGoalLevels: hoverGoalLevelsRef.current,
      highlightGroupId: highlightGroupIdRef.current,
    });
    const candle = (nextOption.series || []).find((row) => row?.type === 'candlestick');
    const series = [];
    if (candle) {
      series.push({
        name: candle.name || 'K线',
        type: 'candlestick',
        markLine: candle.markLine || { symbol: 'none', data: [] },
      });
    }
    (nextOption.series || []).forEach((row) => {
      if (row?.type !== 'scatter') return;
      series.push({
        name: row.name,
        type: 'scatter',
        symbolSize: row.symbolSize,
      });
    });
    try {
      instance.setOption({ series }, { lazyUpdate: true, silent: true });
    } catch (_err) {
      // mousemove 途中偶发；下一帧可再试
    }
  }, []);

  const scheduleHoverOverlaySync = useCallback(() => {
    if (syncRafRef.current != null) cancelAnimationFrame(syncRafRef.current);
    syncRafRef.current = requestAnimationFrame(() => {
      syncRafRef.current = null;
      syncHoverOverlay();
    });
  }, [syncHoverOverlay]);

  const setHighlightGroup = useCallback((groupId) => {
    const nextId = String(groupId || '').trim() || null;
    if (highlightGroupIdRef.current === nextId) return;
    highlightGroupIdRef.current = nextId;
    scheduleHoverOverlaySync();
  }, [scheduleHoverOverlaySync]);

  const chartModel = useMemo(
    () => stockKlinePayloadToMarketChartModel(payload),
    [payload],
  );

  const candleDates = useMemo(
    () => (payload?.candles || []).map((c) => String(c?.date || '').trim()).filter(Boolean),
    [payload],
  );

  const hasFinanceLayer = useMemo(() => {
    if ((chartModel?.financeEvents || []).length > 0) return true;
    return (payload?.chart_layers || []).some((l) => String(l?.role || '') === 'event_pins');
  }, [chartModel, payload]);

  const financeSnapshot = useMemo(() => {
    const events = chartModel?.financeEvents;
    if (!pointerAsOf || !events?.length) return null;
    return pickFinanceSnapshot(events, pointerAsOf);
  }, [chartModel, pointerAsOf]);

  const financeLive = Boolean(pointerAsOf && financeSnapshot);

  const resolveDateFromAxisEvent = useCallback((params) => (
    resolveAxisPointerDate(params, candleDates)
  ), [candleDates]);

  const resolveDateFromDataZoom = useCallback((params) => {
    const batch = Array.isArray(params?.batch) && params.batch.length
      ? params.batch[0]
      : params;
    if (!candleDates.length) return '';
    const n = candleDates.length;
    const endPct = Number(batch?.end);
    const pct = Number.isFinite(endPct) ? endPct : 100;
    const idx = Math.min(n - 1, Math.max(0, Math.round((pct / 100) * (n - 1))));
    return candleDates[idx] || '';
  }, [candleDates]);

  const chartEvents = useMemo(() => ({
    updateAxisPointer: (params) => {
      const d = resolveDateFromAxisEvent(params);
      if (!d) return;
      setPointerAsOf(d);
      const levels = buyLevelsByDate.get(d) || null;
      const prev = hoverGoalLevelsRef.current;
      const same = (prev == null && levels == null)
        || (Array.isArray(prev) && Array.isArray(levels)
          && prev.length === levels.length
          && prev.every((row, i) => row?.price === levels[i]?.price && row?.kind === levels[i]?.kind));
      if (!same) {
        hoverGoalLevelsRef.current = levels;
        scheduleHoverOverlaySync();
      }
    },
    mouseover: (params) => {
      if (params?.seriesType !== 'scatter') return;
      if (clearHighlightTimerRef.current) {
        clearTimeout(clearHighlightTimerRef.current);
        clearHighlightTimerRef.current = null;
      }
      const gid = String(params?.data?._markerMeta?.groupId || '').trim();
      setHighlightGroup(gid || null);
    },
    mouseout: (params) => {
      if (params?.seriesType !== 'scatter') return;
      // 多段止盈同 series 点间移动会先 out 再 over；延迟清除避免拆 series
      if (clearHighlightTimerRef.current) clearTimeout(clearHighlightTimerRef.current);
      clearHighlightTimerRef.current = setTimeout(() => {
        clearHighlightTimerRef.current = null;
        setHighlightGroup(null);
      }, 80);
    },
    datazoom: (params) => {
      const d = resolveDateFromDataZoom(params);
      if (d) zoomEndDateRef.current = d;
      setPointerAsOf('');
      hoverGoalLevelsRef.current = null;
      if (clearHighlightTimerRef.current) {
        clearTimeout(clearHighlightTimerRef.current);
        clearHighlightTimerRef.current = null;
      }
      setHighlightGroup(null);
    },
    globalout: () => {
      setPointerAsOf('');
      hoverGoalLevelsRef.current = null;
      if (clearHighlightTimerRef.current) {
        clearTimeout(clearHighlightTimerRef.current);
        clearHighlightTimerRef.current = null;
      }
      setHighlightGroup(null);
    },
  }), [
    buyLevelsByDate,
    resolveDateFromAxisEvent,
    resolveDateFromDataZoom,
    scheduleHoverOverlaySync,
    setHighlightGroup,
  ]);

  const layerHints = useMemo(() => {
    const layers = payload?.chart_layers || [];
    if (!layers.length) return '';
    return layers.map((l) => l.label || l.role).filter(Boolean).join(' · ');
  }, [payload]);

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

  const subPanelSummary = (() => {
    const panels = new Set(
      (payload?.indicator_series || [])
        .map((s) => s?.panel)
        .filter((p) => p && p !== 'overlay'),
    );
    const names = [];
    if (panels.has('macd')) names.push('MACD');
    if (panels.has('oscillator')) names.push('振荡指标');
    if ([...panels].some((p) => p !== 'macd' && p !== 'oscillator' && p !== 'volume')) {
      names.push('其它副图');
    }
    return names.join(' / ');
  })();

  const hasVolume = (payload?.candles || []).some(
    (c) => c?.volume != null && Number.isFinite(Number(c.volume)),
  );

  const hasChart = Object.keys(chartOption).length > 0;

  return (
    <Dialog
      open={Boolean(open && stock)}
      onClose={onClose}
      fullScreen
      className="ntq-report-stock-detail-dialog"
    >
      <DialogTitle
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 2,
          py: 1.25,
          pr: 1,
        }}
      >
        <Typography variant="subtitle1" fontWeight={700} component="span">
          {stockCode}
          {stockName && stockName !== stockCode ? ` · ${stockName}` : ''}
          <Typography
            component="span"
            variant="caption"
            color="text.secondary"
            sx={{ ml: 1.5 }}
          >
            逐股审阅
          </Typography>
        </Typography>
        <IconButton aria-label="关闭" onClick={onClose} edge="end">
          <NtqIcon name="cancel" size={18} />
        </IconButton>
      </DialogTitle>
      <DialogContent dividers sx={{ display: 'flex', flexDirection: 'column', gap: 1.25, pt: 1.5 }}>
        <BacktestPeriodBanner slot={periodSlot} />
        {payload?.candles?.length ? (
          <Typography variant="caption" color="text.secondary" component="div">
            <Box component="div">
              主图：K线（前复权）
              {hasVolume ? ' · 成交量' : ''}
              {layerHints ? ` · 分层：${layerHints}` : ''}
            </Box>
            <Box component="div">
              {subPanelSummary ? `副图：${subPanelSummary} · ` : ''}
              拖动底部滑块缩放；Y 轴随可见区间自适应
            </Box>
          </Typography>
        ) : null}

        {loading ? (
          <InlineLoadingState block message="正在加载 K 线与标注…" />
        ) : (
          <>
            {error ? (
              <Typography variant="body2" color="error">{error}</Typography>
            ) : null}
            <Box
              sx={{
                flex: '1 1 auto',
                minHeight: { xs: 420, sm: 560, md: 'calc(100vh - 280px)' },
                width: '100%',
              }}
            >
              {hasChart ? (
                <ReactECharts
                  ref={chartRef}
                  option={chartOption}
                  style={{ height: '100%', width: '100%', minHeight: 520 }}
                  notMerge
                  lazyUpdate
                  onEvents={chartEvents}
                />
              ) : (
                <Typography variant="body2" color="text.secondary">
                  暂无 K 线数据
                </Typography>
              )}
            </Box>
            {hasFinanceLayer ? (
              <FinancePitCard
                visible
                live={financeLive}
                pointerAsOf={pointerAsOf}
                snapshot={financeSnapshot}
              />
            ) : null}
            {hasChart && activeLayer === 'enum' ? (
              <Typography variant="caption" color="text.secondary" component="div">
                标注：青 pin 为机会触发日；淡紫虚竖线为财报公告日（详情见下方 PIT 卡）。
              </Typography>
            ) : null}
            {hasChart && activeLayer === 'price' ? (
              <Typography variant="caption" color="text.secondary" component="div">
                标注：青 pin 买入；中间止盈/止损/保护/动态分色；交易完成按盈亏红绿（随 market profile）；
                到期/回测结束为中性。十字线停在买入日时显示计划止盈/止损虚线；淡紫竖线为财报日。
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
      </DialogContent>
    </Dialog>
  );
}

export default ReportStockDetailView;
