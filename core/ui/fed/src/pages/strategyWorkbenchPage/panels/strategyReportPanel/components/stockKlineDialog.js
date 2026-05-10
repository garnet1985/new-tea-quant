import React from 'react';
import { Dialog, DialogContent, DialogTitle, Typography } from '@mui/material';
import ReactECharts from 'echarts-for-react';
import { formatReportChartDateLabel } from '../reportDateFormat';

function hashString(text) {
  let hash = 0;
  for (let i = 0; i < text.length; i += 1) hash = ((hash << 5) - hash) + text.charCodeAt(i);
  return Math.abs(hash);
}

export function buildStockKlineChartOption(stock) {
  if (!stock) return {};
  const seed = hashString(stock.stockCode);
  const points = 42;
  const dates = Array.from({ length: points }).map((_, index) => `D${index + 1}`);
  const base = 80 + (seed % 120);
  let prevClose = base;
  const candleData = dates.map((_, index) => {
    const drift = Math.sin((index + (seed % 7)) / 4.5) * 1.7 + ((seed + index) % 5 - 2) * 0.35;
    const open = Number((prevClose + drift * 0.4).toFixed(2));
    const close = Number((open + drift).toFixed(2));
    const high = Number((Math.max(open, close) + 0.8 + ((seed + index) % 3) * 0.35).toFixed(2));
    const low = Number((Math.min(open, close) - 0.8 - ((seed + index) % 2) * 0.4).toFixed(2));
    prevClose = close;
    return [open, close, low, high];
  });
  const buyIndex = 9;
  const sellIndex = 31;
  const buyPrice = candleData[buyIndex]?.[1];
  const sellPrice = candleData[sellIndex]?.[1];

  return {
    animation: false,
    grid: { left: 36, right: 12, top: 20, bottom: 28 },
    xAxis: {
      type: 'category',
      data: dates,
      scale: true,
      boundaryGap: true,
      axisLine: { lineStyle: { color: '#D0D7DE' } },
      axisLabel: {
        color: '#5F6368',
        fontSize: 10,
        formatter: (v) => formatReportChartDateLabel(v),
      },
    },
    yAxis: {
      scale: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#5F6368', fontSize: 10 },
      splitLine: { lineStyle: { color: '#ECEFF1' } },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    series: [
      {
        type: 'candlestick',
        data: candleData,
        itemStyle: {
          color: '#ef5350',
          color0: '#26a69a',
          borderColor: '#ef5350',
          borderColor0: '#26a69a',
        },
      },
      {
        type: 'scatter',
        symbolSize: 10,
        data: [
          { value: [buyIndex, buyPrice], itemStyle: { color: '#2E7D32' }, label: { show: true, formatter: '买入', position: 'top' } },
          { value: [sellIndex, sellPrice], itemStyle: { color: '#C62828' }, label: { show: true, formatter: '卖出', position: 'top' } },
        ],
        tooltip: {
          formatter: (params) => `${params.data?.label?.formatter || '点位'}：${params.value?.[1] || '--'}`,
        },
      },
    ],
  };
}

function buildStockKlineChartOptionFromApi(payload) {
  if (!payload || !Array.isArray(payload.candles) || payload.candles.length === 0) return {};
  const dates = payload.candles.map((item) => item.date);
  const candleData = payload.candles.map((item) => [item.open, item.close, item.low, item.high]);
  const markerData = Array.isArray(payload.markers)
    ? payload.markers.map((item) => ({
      value: [dates.indexOf(item.date), item.price],
      itemStyle: { color: item.type === 'buy' ? '#2E7D32' : '#C62828' },
      label: {
        show: true,
        formatter: item.type === 'buy' ? '买入' : '卖出',
        position: 'top',
      },
    })).filter((item) => item.value[0] >= 0)
    : [];
  return {
    animation: false,
    grid: { left: 36, right: 12, top: 20, bottom: 28 },
    xAxis: {
      type: 'category',
      data: dates,
      scale: true,
      boundaryGap: true,
      axisLine: { lineStyle: { color: '#D0D7DE' } },
      axisLabel: {
        color: '#5F6368',
        fontSize: 10,
        formatter: (v) => formatReportChartDateLabel(v),
      },
    },
    yAxis: {
      scale: true,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#5F6368', fontSize: 10 },
      splitLine: { lineStyle: { color: '#ECEFF1' } },
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter(params) {
        const arr = Array.isArray(params) ? params : [params];
        if (!arr.length) return '';
        const lines = [formatReportChartDateLabel(arr[0].axisValue)];
        arr.forEach((p) => {
          if (p.seriesType === 'candlestick') {
            const row = Array.isArray(p.value) && p.value.length >= 4
              ? p.value
              : (Array.isArray(p.data) ? p.data : null);
            if (Array.isArray(row) && row.length >= 4) {
              const [o, c, l, h] = row;
              lines.push(`开盘 ${o}　收盘 ${c}　最低 ${l}　最高 ${h}`);
            }
          } else if (p.seriesType === 'scatter') {
            const y = Array.isArray(p.value) ? p.value[1] : null;
            const tag = p.data?.label?.formatter || '点位';
            if (y != null && Number.isFinite(Number(y))) lines.push(`${tag}：${y}`);
          }
        });
        return lines.filter(Boolean).join('<br/>');
      },
    },
    series: [
      {
        type: 'candlestick',
        data: candleData,
        itemStyle: {
          color: '#ef5350',
          color0: '#26a69a',
          borderColor: '#ef5350',
          borderColor0: '#26a69a',
        },
      },
      {
        type: 'scatter',
        symbolSize: 10,
        data: markerData,
      },
    ],
  };
}

function StockKlineDialog({
  open,
  stock,
  klineData,
  loading = false,
  error = '',
  onClose,
}) {
  const option = klineData
    ? buildStockKlineChartOptionFromApi(klineData)
    : buildStockKlineChartOption(stock);
  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        {stock ? `${stock.stockCode} · ${stock.stockName}` : 'K 线详情'}
      </DialogTitle>
      <DialogContent dividers>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          展示该股票区间 K 线，以及本次回测中的买入/卖出点位。
        </Typography>
        {loading ? (
          <Typography variant="caption" color="text.secondary">正在加载 K 线数据...</Typography>
        ) : null}
        {error ? (
          <Typography variant="caption" color="error">{error}</Typography>
        ) : null}
        <ReactECharts
          option={option}
          style={{ height: 420, width: '100%' }}
          notMerge
          lazyUpdate
        />
      </DialogContent>
    </Dialog>
  );
}

export default StockKlineDialog;
