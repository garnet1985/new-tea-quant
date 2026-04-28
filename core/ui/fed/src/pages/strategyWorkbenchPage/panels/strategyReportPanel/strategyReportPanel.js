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
import CompareVersionSelect from 'components/compareVersionSelect/compareVersionSelect';
import {
  MOCK_REPORT_CAPITAL_SUMMARIES_BY_VERSION,
  MOCK_REPORT_ENUM_OPPORTUNITIES_BY_VERSION,
  MOCK_REPORT_PRICE_SUMMARIES_BY_VERSION,
  STRATEGY_WORKBENCH_COMPARE_VERSION_OPTIONS,
} from '../../mocks/strategyWorkbenchMocks';
import {
  buildCapitalMetrics,
  buildCapitalMetricsFromBase,
  buildEnumMetrics,
  buildEnumMetricsFromTotal,
  buildPriceMetrics,
  buildPriceMetricsFromBase,
} from '../../mocks/strategyReportMetrics';

const STEP_TABS = [
  { key: 'enum', label: '枚举报告' },
  { key: 'price', label: '价格回测报告' },
  { key: 'capital', label: '资金模拟报告' },
];

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

  const renderReportByTab = (tabKey, reportData, title, options = {}) => {
    if (tabKey === 'enum') {
      return (
        <OpportunityEnumrateReport
          metrics={reportData?.enumMetrics}
          title={title}
          showStockGrid={options.showStockGrid !== false}
        />
      );
    }
    if (tabKey === 'price') {
      return (
        <PriceFactorReport
          metrics={reportData?.priceMetrics}
          title={title}
          showStockGrid={options.showStockGrid !== false}
        />
      );
    }
    if (tabKey === 'capital') {
      return (
        <CapitalAllocationReport
          metrics={reportData?.capitalMetrics}
          title={title}
          showStockGrid={options.showStockGrid !== false}
        />
      );
    }
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

    return renderReportByTab('capital', { capitalMetrics: buildCapitalMetrics(executionState) }, '资金模拟报告（草图）');
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
              options={STRATEGY_WORKBENCH_COMPARE_VERSION_OPTIONS}
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
                    capitalMetrics: buildCapitalMetrics(executionState),
                  },
                  '本次报告',
                  { showStockGrid: false },
                )}
              </Stack>
              <Stack spacing={1}>
                <Typography variant="subtitle2" fontWeight={700}>对比版本结果</Typography>
                {compareVersion
                  ? renderReportByTab(
                    resolvedActiveTab,
                    {
                      enumMetrics: buildEnumMetricsFromTotal(MOCK_REPORT_ENUM_OPPORTUNITIES_BY_VERSION[compareVersion] || 0),
                      priceMetrics: buildPriceMetricsFromBase(MOCK_REPORT_PRICE_SUMMARIES_BY_VERSION[compareVersion]),
                      capitalMetrics: buildCapitalMetricsFromBase(MOCK_REPORT_CAPITAL_SUMMARIES_BY_VERSION[compareVersion]),
                    },
                    `对比报告（${compareVersion}）`,
                    { showStockGrid: false },
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
