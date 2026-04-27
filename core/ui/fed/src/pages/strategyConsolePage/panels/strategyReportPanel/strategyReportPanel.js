import React, { useMemo, useState } from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  Stack,
  Tab,
  Tabs,
  Typography,
} from '@mui/material';
import OpportunityEnumrateReport from './reports/opportunityEnumerate';
import PriceFactorReport from './reports/priceFactor';
import CapitalAllocationReport from './reports/capitalAllocation';
import CompareVersionSelect from './components/compareVersionSelect';

const STEP_TABS = [
  { key: 'enum', label: '枚举报告' },
  { key: 'price', label: '价格回测报告' },
  { key: 'capital', label: '资金模拟报告' },
];
const REPORT_COMPARE_OPTIONS = ['latest', 'v3', 'v2', 'v1'];
const MOCK_ENUM_OPPORTUNITIES = { latest: 100, v3: 108, v2: 103, v1: 115 };
const MOCK_PRICE_SUMMARIES = {
  latest: { winRate: 56.2, roi: 18.4, avgHoldDays: 13.1 },
  v3: { winRate: 52.8, roi: 12.6, avgHoldDays: 16.2 },
  v2: { winRate: 49.6, roi: 9.3, avgHoldDays: 14.5 },
  v1: { winRate: 44.1, roi: 6.7, avgHoldDays: 18.9 },
};

function buildEnumMetricsFromTotal(totalOpportunities) {
  if (totalOpportunities <= 0) return null;

  // 先用稳定 mock 规则构建 UI 骨架，后续接真实枚举 summary
  const totalStocks = 150;
  const triggerStocks = Math.max(1, Math.round(totalOpportunities * 0.42));
  const triggerRatio = Number(((triggerStocks / totalStocks) * 100).toFixed(1));
  const avgPerStock = totalOpportunities / triggerStocks;
  const p10 = Math.max(0.4, Number((avgPerStock * 0.38).toFixed(2)));
  const p20 = Math.max(0.5, Number((avgPerStock * 0.48).toFixed(2)));
  const p30 = Math.max(0.6, Number((avgPerStock * 0.62).toFixed(2)));
  const p40 = Math.max(0.7, Number((avgPerStock * 0.76).toFixed(2)));
  const p50 = Number((avgPerStock * 0.9).toFixed(2));
  const p60 = Number((avgPerStock * 1.04).toFixed(2));
  const p70 = Number((avgPerStock * 1.2).toFixed(2));
  const p75 = Number((avgPerStock * 1.35).toFixed(2));
  const p80 = Number((avgPerStock * 1.5).toFixed(2));
  const p90 = Number((avgPerStock * 1.72).toFixed(2));
  const completedRatio = Number((58 + Math.min(30, totalOpportunities / 5)).toFixed(1));
  const completedCount = Math.round((completedRatio / 100) * totalOpportunities);

  const meanGap = Number((6 + (120 / Math.max(20, totalOpportunities))).toFixed(2));
  const meanDuration = Number((4 + totalOpportunities / 18).toFixed(2));
  const stdGap = Number((meanGap * 0.62).toFixed(2));
  const cv = Number((stdGap / meanGap).toFixed(2));

  const dispersionConclusion = cv < 0.45
    ? '机会出现较均匀，节奏相对稳定'
    : (cv < 0.8 ? '机会有一定聚集，节奏波动中等' : '机会集中出现，节奏波动较大');

  const percentileLabels = ['10%分位', '20%分位', '30%分位', '40%分位', '50%分位', '60%分位', '70%分位', '80%分位', '90%分位'];
  const percentileValues = [p10, p20, p30, p40, p50, p60, p70, p80, p90];

  return {
    totalOpportunities,
    totalStocks,
    triggerStocks,
    triggerRatio,
    avgPerStock,
    p10,
    p20,
    p30,
    p40,
    p50,
    p60,
    p70,
    p75,
    p80,
    p90,
    completedRatio,
    completedCount,
    meanGap,
    meanDuration,
    stdGap,
    cv,
    dispersionConclusion,
    percentileLabels,
    percentileValues,
  };
}

function buildEnumMetrics(executionState) {
  const totalOpportunities = Number(executionState?.result?.enum?.opportunities || 0);
  return buildEnumMetricsFromTotal(totalOpportunities);
}

function buildPriceMetricsFromBase(base) {
  if (!base) return null;
  const winRate = Number(base.winRate || 0);
  const avgRoi = Number(base.roi || 0);
  const avgDurationDays = Number(base.avgHoldDays || 0);

  const totalInvestments = Math.max(18, Math.round(36 + winRate * 1.4));
  const totalWinInvestments = Math.round(totalInvestments * (winRate / 100));
  const totalLossInvestments = Math.max(0, totalInvestments - totalWinInvestments - 2);
  const totalOpenInvestments = totalInvestments - totalWinInvestments - totalLossInvestments;
  const stocksWithOpportunities = Math.max(8, Math.round(totalInvestments / 2.8));
  const avgInvestmentsPerStock = Number((totalInvestments / stocksWithOpportunities).toFixed(2));

  const annualReturn = avgDurationDays > 0
    ? Number((avgRoi * (365 / avgDurationDays)).toFixed(2))
    : 0;
  const avgProfitPerInvestment = Math.round(12000 + avgRoi * 1400);
  const avgProfitPerStock = Math.round(avgProfitPerInvestment * avgInvestmentsPerStock);

  const roiP10 = Number((avgRoi * 0.28).toFixed(2));
  const roiP20 = Number((avgRoi * 0.42).toFixed(2));
  const roiP30 = Number((avgRoi * 0.58).toFixed(2));
  const roiP40 = Number((avgRoi * 0.73).toFixed(2));
  const roiP50 = Number((avgRoi * 0.92).toFixed(2));
  const roiP60 = Number((avgRoi * 1.07).toFixed(2));
  const roiP70 = Number((avgRoi * 1.22).toFixed(2));
  const roiP80 = Number((avgRoi * 1.38).toFixed(2));
  const roiP90 = Number((avgRoi * 1.55).toFixed(2));
  const roiP25 = Number(((roiP20 + roiP30) / 2).toFixed(2));
  const roiP75 = Number(((roiP70 + roiP80) / 2).toFixed(2));
  const roiIqr = Number((roiP75 - roiP25).toFixed(2));
  const roiBucketEdges = [-50, -40, -30, -20, -10, 0, 10, 20, 30, 40, 50];
  const roiBucketLabels = roiBucketEdges.slice(0, -1).map((start, index) => {
    const end = roiBucketEdges[index + 1];
    return `${start}%~${end}%`;
  });
  const sigma = 18;
  const roiBucketWeights = roiBucketEdges.slice(0, -1).map((start, index) => {
    const center = (start + roiBucketEdges[index + 1]) / 2;
    return Math.exp(-((center - avgRoi) ** 2) / (2 * sigma * sigma));
  });
  const weightSum = roiBucketWeights.reduce((sum, weight) => sum + weight, 0) || 1;
  const rawCounts = roiBucketWeights.map((weight) => (weight / weightSum) * totalInvestments);
  const roiBucketCounts = rawCounts.map((value) => Math.floor(value));
  let remaining = totalInvestments - roiBucketCounts.reduce((sum, count) => sum + count, 0);
  const remainders = rawCounts
    .map((value, index) => ({ index, remainder: value - Math.floor(value) }))
    .sort((a, b) => b.remainder - a.remainder);
  for (let i = 0; i < remainders.length && remaining > 0; i += 1) {
    roiBucketCounts[remainders[i].index] += 1;
    remaining -= 1;
  }

  const roiConclusion = roiP50 > 0 && roiP25 > 0
    ? '中位与下分位均为正，收益结构较稳'
    : (roiP50 > 0 ? '中位收益为正，但下分位承压' : '中位收益偏弱，需关注策略有效性');

  return {
    winRate: Number(winRate.toFixed(1)),
    avgRoi: Number(avgRoi.toFixed(2)),
    avgDurationDays: Number(avgDurationDays.toFixed(1)),
    annualReturn,
    totalInvestments,
    totalWinInvestments,
    totalLossInvestments,
    totalOpenInvestments,
    stocksWithOpportunities,
    avgInvestmentsPerStock,
    avgProfitPerInvestment,
    avgProfitPerStock,
    roiP10,
    roiP20,
    roiP30,
    roiP40,
    roiP50,
    roiP60,
    roiP70,
    roiP80,
    roiP90,
    roiP25,
    roiP75,
    roiIqr,
    roiConclusion,
    roiBucketLabels,
    roiBucketCounts,
    roiPercentileLabels: ['10%分位', '20%分位', '30%分位', '40%分位', '50%分位', '60%分位', '70%分位', '80%分位', '90%分位'],
    roiPercentileValues: [roiP10, roiP20, roiP30, roiP40, roiP50, roiP60, roiP70, roiP80, roiP90],
  };
}

function buildPriceMetrics(executionState) {
  const base = executionState?.result?.price || MOCK_PRICE_SUMMARIES.latest;
  return buildPriceMetricsFromBase(base);
}

function StrategyReportPanel({ executionState }) {
  const availableTabs = useMemo(() => {
    const stepStatus = executionState?.stepStatus || {};
    return STEP_TABS.filter((tab) => stepStatus[tab.key] === 'done');
  }, [executionState]);

  const [activeTab, setActiveTab] = useState('');
  const [compareDialogOpen, setCompareDialogOpen] = useState(false);
  const [compareVersion, setCompareVersion] = useState('');

  const resolvedActiveTab = useMemo(() => {
    if (availableTabs.length === 0) return '';
    if (availableTabs.some((tab) => tab.key === activeTab)) return activeTab;
    return availableTabs[availableTabs.length - 1].key;
  }, [activeTab, availableTabs]);

  const handleTabChange = (_event, nextValue) => {
    setActiveTab(nextValue);
  };

  const renderReportByTab = (tabKey, reportData, title) => {
    if (tabKey === 'enum') return <OpportunityEnumrateReport metrics={reportData?.enumMetrics} title={title} />;
    if (tabKey === 'price') return <PriceFactorReport metrics={reportData?.priceMetrics} title={title} />;
    if (tabKey === 'capital') return <CapitalAllocationReport title={title} />;
    return null;
  };

  const renderTabContent = () => {
    if (!resolvedActiveTab) {
      return (
        <Typography variant="body2" color="text.secondary">
          先执行任一步，系统会在这里自动新增对应报告 Tab。
        </Typography>
      );
    }

    if (resolvedActiveTab === 'enum') {
      const enumMetrics = buildEnumMetrics(executionState);
      if (!enumMetrics) {
        return (
          <Typography variant="body2" color="text.secondary">
            枚举步骤已完成，等待汇总指标（Placeholder：后续接真实枚举 summary）。
          </Typography>
        );
      }
      return renderReportByTab('enum', { enumMetrics }, '枚举核心结论（草图）');
    }

    if (resolvedActiveTab === 'price') {
      return renderReportByTab('price', { priceMetrics: buildPriceMetrics(executionState) }, '价格回测报告（草图）');
    }

    return renderReportByTab('capital', {}, '资金模拟报告（Placeholder）');
  };

  return (
    <Accordion defaultExpanded disableGutters>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography fontWeight={600}>模拟结果</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1.25}>
          {availableTabs.length > 0 ? (
            <Tabs
              value={resolvedActiveTab}
              onChange={handleTabChange}
              variant="scrollable"
              scrollButtons="auto"
            >
              {availableTabs.map((tab) => (
                <Tab key={tab.key} value={tab.key} label={tab.label} />
              ))}
            </Tabs>
          ) : null}
          <Stack direction="row" justifyContent="flex-end">
            <Button
              size="small"
              variant="outlined"
              disabled={!resolvedActiveTab}
              onClick={() => setCompareDialogOpen(true)}
            >
              对比结果
            </Button>
          </Stack>
          {renderTabContent()}
          <Divider />
          <Typography variant="caption" color="text.secondary">
            注：当前为 UI 草图数据（由执行结果 mock 推导）。确认样式后可直接替换为真实汇总统计。
          </Typography>
        </Stack>
      </AccordionDetails>

      <Dialog open={compareDialogOpen} onClose={() => setCompareDialogOpen(false)} maxWidth="lg" fullWidth>
        <DialogTitle>报告对比</DialogTitle>
        <DialogContent dividers>
          <Stack spacing={1.25}>
            <CompareVersionSelect
              value={compareVersion}
              onChange={setCompareVersion}
              options={REPORT_COMPARE_OPTIONS}
              label="选择对比版本"
              includeEmpty
              emptyLabel="不对比"
            />

            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
                gap: 1.25,
                alignItems: 'start',
              }}
            >
              <Stack spacing={1}>
                <Typography variant="subtitle2" fontWeight={700}>本次结果</Typography>
                {renderReportByTab(
                  resolvedActiveTab,
                  {
                    enumMetrics: buildEnumMetrics(executionState),
                    priceMetrics: buildPriceMetrics(executionState),
                  },
                  '本次报告',
                )}
              </Stack>
              <Stack spacing={1}>
                <Typography variant="subtitle2" fontWeight={700}>对比版本结果</Typography>
                {compareVersion
                  ? renderReportByTab(
                    resolvedActiveTab,
                    {
                      enumMetrics: buildEnumMetricsFromTotal(MOCK_ENUM_OPPORTUNITIES[compareVersion] || 0),
                      priceMetrics: buildPriceMetricsFromBase(MOCK_PRICE_SUMMARIES[compareVersion]),
                    },
                    `对比报告（${compareVersion}）`,
                  )
                  : (
                    <Box
                      sx={{
                        border: 1,
                        borderColor: 'divider',
                        borderRadius: 1,
                        p: 2,
                        backgroundColor: 'background.paper',
                      }}
                    >
                      <Typography variant="body2" color="text.secondary">
                        请选择对比版本后查看结果。
                      </Typography>
                    </Box>
                  )}
              </Stack>
            </Box>
          </Stack>
        </DialogContent>
      </Dialog>
    </Accordion>
  );
}

export default StrategyReportPanel;
