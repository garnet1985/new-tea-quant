import React, { useMemo, useState } from 'react';
import { Box, Stack, Typography } from '@mui/material';
import ReactECharts from 'echarts-for-react';
import { buildPriceSampleStockRows } from '../../../mocks/strategyReportSampleRows';
import { REPORT_BLOCK_UNAVAILABLE_ZH } from '../../../mocks/strategyReportMetrics';
import MetricCard from 'components/metricCard/metricCard';
import { SectionBlock } from 'components/sectionBlock/sectionBlock';
import ReportStockSampleGrid from 'components/reportStockSampleGrid/reportStockSampleGrid';

const EMPTY_METRICS_BASE = {
  totalInvestments: 0,
  winRate: 0,
  avgRoi: 0,
  avgDurationDays: 0,
};

const BAR_RADIUS = 4;

/** 纵轴柱状图：正值圆角朝上侧（顶端），负值圆角朝外侧（底端），避免负柱圆角挤在 X 轴一侧 */
function signedVerticalBarItems(values) {
  if (!Array.isArray(values)) return [];
  return values.map((v) => {
    const n = Number(v);
    if (!Number.isFinite(n)) {
      return { value: 0, itemStyle: { borderRadius: [BAR_RADIUS, BAR_RADIUS, 0, 0] } };
    }
    if (n >= 0) {
      return { value: n, itemStyle: { borderRadius: [BAR_RADIUS, BAR_RADIUS, 0, 0] } };
    }
    return { value: n, itemStyle: { borderRadius: [0, 0, BAR_RADIUS, BAR_RADIUS] } };
  });
}

function tooltipPrimaryValue(point) {
  const raw = point?.data;
  if (raw != null && typeof raw === 'object' && Object.prototype.hasOwnProperty.call(raw, 'value')) {
    return raw.value;
  }
  return raw;
}

/** 旧版会话摘要里的固定 ROI 档位（与新版的 [min,max] 等分标签区分） */
function looksLikeLegacyFixedRoiBuckets(labels) {
  if (!Array.isArray(labels)) return false;
  return labels.some((t) => (
    typeof t === 'string'
    && (t.includes('≤-20') || t.includes('>50%') || /\(-20,-5]/.test(t))
  ));
}

function UnavailableHint() {
  return (
    <Typography variant="body2" color="text.secondary" sx={{ py: 0.5 }}>
      {REPORT_BLOCK_UNAVAILABLE_ZH}
    </Typography>
  );
}

function buildRoiDistributionOption(metrics) {
  return {
    animation: false,
    grid: { left: 30, right: 10, top: 20, bottom: 28 },
    xAxis: {
      type: 'category',
      data: metrics.roiPercentileLabels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#D0D7DE' } },
      axisLabel: { color: '#5F6368', fontSize: 11 },
    },
    yAxis: {
      type: 'value',
      splitNumber: 3,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#5F6368', fontSize: 11, formatter: '{value}%' },
      splitLine: { lineStyle: { color: '#ECEFF1' } },
    },
    series: [
      {
        type: 'bar',
        data: signedVerticalBarItems(metrics.roiPercentileValues),
        barMaxWidth: 28,
        itemStyle: { color: '#36A2EB' },
      },
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        const val = tooltipPrimaryValue(point);
        return `${point.axisValue}<br/>ROI：${val}%`;
      },
    },
  };
}

function buildRoiBucketOption(metrics) {
  return {
    animation: false,
    grid: { left: 30, right: 10, top: 20, bottom: 50 },
    xAxis: {
      type: 'category',
      data: metrics.roiBucketLabels,
      axisTick: { show: false },
      axisLine: { lineStyle: { color: '#D0D7DE' } },
      axisLabel: { color: '#5F6368', fontSize: 10, interval: 0, rotate: 25 },
    },
    yAxis: {
      type: 'value',
      splitNumber: 3,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#5F6368', fontSize: 11 },
      splitLine: { lineStyle: { color: '#ECEFF1' } },
    },
    series: [
      {
        type: 'bar',
        data: metrics.roiBucketCounts,
        barMaxWidth: 24,
        itemStyle: { color: '#7A8DF5', borderRadius: [4, 4, 0, 0] },
      },
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const point = params?.[0];
        if (!point) return '';
        return `${point.axisValue}<br/>投资次数：${point.data}`;
      },
    },
  };
}

function PriceFactorReport({
  metrics,
  stockRows,
  strategyName: _strategyName,
  runId: _runId,
  title = '价格回测报告',
  showStockGrid = true,
}) {
  const [stockSearch, setStockSearch] = useState('');

  const avail = metrics?._availability ?? {
    overview: false,
    sampleCoverage: false,
    profitBasics: false,
    roiPercentileViz: false,
    roiBucketViz: false,
  };

  const derivedStockRows = useMemo(() => {
    if (Array.isArray(stockRows) && stockRows.length > 0) return stockRows;
    const base = metrics || EMPTY_METRICS_BASE;
    return buildPriceSampleStockRows(base);
  }, [metrics, stockRows]);

  const filteredRows = useMemo(() => {
    const keyword = stockSearch.trim().toLowerCase();
    const filtered = keyword
      ? derivedStockRows.filter((row) => (
        row.stockCode.toLowerCase().includes(keyword) || row.stockName.toLowerCase().includes(keyword)
      ))
      : derivedStockRows;
    return filtered;
  }, [derivedStockRows, stockSearch]);

  const stockColumns = useMemo(() => [
    { field: 'stockCode', headerName: '代码', flex: 1, minWidth: 120 },
    { field: 'stockName', headerName: '名称', flex: 1, minWidth: 120 },
    {
      field: 'winRate',
      headerName: '胜率',
      width: 110,
      valueFormatter: (params) => `${params.value}%`,
    },
    {
      field: 'roi',
      headerName: 'ROI',
      width: 110,
      valueFormatter: (params) => `${params.value > 0 ? '+' : ''}${params.value}%`,
    },
    {
      field: 'holdDays',
      headerName: '平均投资天数',
      width: 110,
      valueFormatter: (params) => `${params.value} 天`,
    },
  ], []);

  if (!metrics || typeof metrics !== 'object') {
    return <UnavailableHint />;
  }

  const volCardHint = (() => {
    if (!avail.roiPercentileViz) return '';
    if (Number.isFinite(metrics.roiStdPct)) {
      return [
        Number.isFinite(metrics.roiP50) ? `P50 ${metrics.roiP50}%` : '',
        Number.isFinite(metrics.roiIqr) ? `IQR ${metrics.roiIqr}%` : '',
      ].filter(Boolean).join(' · ');
    }
    return [
      Number.isFinite(metrics.roiIqr) ? `IQR ${metrics.roiIqr}%` : '',
      metrics.roiConclusion || '',
    ].filter(Boolean).join(' · ');
  })();

  return (
    <Stack spacing={1.25}>
      <Typography variant="subtitle2" fontWeight={600}>{title}</Typography>

      <Typography variant="caption" color="text.secondary">
        K 线与买卖点透视暂未启用（需加载行情并描点后再接）。
      </Typography>

      {showStockGrid ? (
        <ReportStockSampleGrid
          title="逐股样本"
          tip="用于查看本次价格回测中单股表现；支持搜索、表头排序与底部分页。（逐股接口接入后将替换占位样本）"
          searchValue={stockSearch}
          onSearchChange={setStockSearch}
          rows={filteredRows}
          columns={stockColumns}
        />
      ) : null}

      <SectionBlock
        title="回测总体"
        tip="用于判断信号层是否具备正向收益，且收益效率是否可接受。"
      >
        {avail.overview ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
            <MetricCard title="胜率" value={`${metrics.winRate}%`} />
            <MetricCard title="平均每笔 ROI" value={`${metrics.avgRoi}%`} />
            <MetricCard title="平均持有时长" value={`${metrics.avgDurationDays} 天`} />
            <MetricCard title="年化收益（自然日）" value={`${metrics.annualReturn}%`} />
          </Box>
        ) : <UnavailableHint />}
      </SectionBlock>

      <SectionBlock
        title="样本与覆盖"
        tip="用于确认结果是否来自足够样本，避免小样本导致结论失真。"
      >
        {avail.sampleCoverage ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
            <MetricCard title="总投资次数" value={metrics.totalInvestments.toLocaleString()} />
            <MetricCard title="产生机会股票数" value={metrics.stocksWithOpportunities.toLocaleString()} />
            <MetricCard title="每股平均投资次数" value={metrics.avgInvestmentsPerStock.toFixed(2)} />
            <MetricCard title="未完成持仓数" value={metrics.totalOpenInvestments.toLocaleString()} />
          </Box>
        ) : <UnavailableHint />}
      </SectionBlock>

      <SectionBlock
        title="盈亏结构（含 ROI 分位）"
        tip="用于观察收益分布是否健康，避免只靠少数大盈利机会拉高均值。"
      >
        {avail.profitBasics ? (
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
            <MetricCard
              title="盈亏次数"
              value={`${metrics.totalWinInvestments} / ${metrics.totalLossInvestments}`}
              hint="赢单 / 亏单"
            />
            <MetricCard title="每笔平均盈利" value={metrics.avgProfitPerInvestment.toLocaleString()} />
            <MetricCard title="每股平均盈利" value={metrics.avgProfitPerStock.toLocaleString()} />
            {avail.roiPercentileViz ? (
              <MetricCard
                title="ROI 波动"
                value={
                  Number.isFinite(metrics.roiStdPct)
                    ? `标准差 ${metrics.roiStdPct}%（样本）`
                    : `P25 ${metrics.roiP25}% · P50 ${metrics.roiP50}% · P75 ${metrics.roiP75}%`
                }
                hint={volCardHint}
              />
            ) : null}
          </Box>
        ) : <UnavailableHint />}
        {!avail.roiPercentileViz ? (
          <Box sx={{ mt: avail.profitBasics ? 1 : 0 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              ROI 分位图：需价格回测摘要中含 roi_percentile_values（长度 9）；会话级汇总正常产出后即展示。
            </Typography>
            <UnavailableHint />
          </Box>
        ) : (
          <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75, mt: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
              ROI 分位图（10% / 20% / … / 90%）
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.75, fontSize: 10 }}>
              横轴为固定的分位点（10%～90%），纵轴为该分位上的 ROI 水平；区间不随样本自动重划。
            </Typography>
            <ReactECharts
              option={buildRoiDistributionOption(metrics)}
              style={{ height: 170, width: '100%' }}
              notMerge
              lazyUpdate
            />
          </Box>
        )}
        {!avail.roiBucketViz ? (
          <Box sx={{ mt: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
              ROI 桶分布：需 roi_bucket_labels / roi_bucket_counts 与摘要一同下发。
            </Typography>
            <UnavailableHint />
          </Box>
        ) : (
          <Box sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 0.75, mt: 1 }}>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
              ROI 收益分布（区间内投资笔数）
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.75, fontSize: 10 }}>
              {metrics.roiBucketBinCount > 0
                ? `将本轮 ROI 的 min～max 等分为 ${metrics.roiBucketBinCount} 段，统计落入各段的投资笔数；末段含右端点 max。`
                : '将本轮 ROI 的 min～max 等分为若干段，统计落入各段的投资笔数；末段含右端点 max。'}
            </Typography>
            {looksLikeLegacyFixedRoiBuckets(metrics.roiBucketLabels) ? (
              <Typography variant="caption" color="warning.main" sx={{ display: 'block', mb: 0.75, fontSize: 10 }}>
                当前摘要仍为旧版固定档位（如 ≤-20%）；请重新执行一次价格回测以写入新版 min～max 等分区间。
              </Typography>
            ) : null}
            <ReactECharts
              option={buildRoiBucketOption(metrics)}
              style={{ height: 190, width: '100%' }}
              notMerge
              lazyUpdate
            />
          </Box>
        )}
      </SectionBlock>
    </Stack>
  );
}

export default PriceFactorReport;
