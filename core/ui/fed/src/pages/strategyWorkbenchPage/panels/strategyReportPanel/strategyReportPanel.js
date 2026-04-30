import React, { useEffect, useMemo, useState } from 'react';
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
  buildCapitalMetrics,
  buildEnumMetrics,
  buildPriceMetrics,
} from '../../mocks/strategyReportMetrics';
import {
  fetchStrategyCompareOptions,
  fetchStrategyReportCompare,
  fetchStrategyReportStocks,
  fetchStrategyReports,
} from '../../../../api/apis/strategyApi';

const STEP_TABS = [
  { key: 'enum', label: '枚举报告' },
  { key: 'price', label: '价格回测报告' },
  { key: 'capital', label: '资金模拟报告' },
];

function StrategyReportPanel({ strategyName, executionState }) {
  const [remoteReports, setRemoteReports] = useState({ reports: {}, availableTabs: [] });
  const [compareOptions, setCompareOptions] = useState(['latest']);
  const [reportStocks, setReportStocks] = useState({ enum: [], price: [], capital: [] });
  const [reportError, setReportError] = useState('');
  const runId = executionState?.runId || '';

  const availableTabs = useMemo(() => {
    const remoteTabs = Array.isArray(remoteReports?.availableTabs)
      ? remoteReports.availableTabs
      : [];
    if (remoteTabs.length > 0) {
      return STEP_TABS.filter((tab) => remoteTabs.includes(tab.key));
    }
    const stepStatus = executionState?.stepStatus || {};
    return STEP_TABS.filter((tab) => stepStatus[tab.key] === 'done');
  }, [executionState, remoteReports]);

  const [activeTab, setActiveTab] = useState('');
  const [compareDialogOpen, setCompareDialogOpen] = useState(false);
  const [compareVersion, setCompareVersion] = useState('');
  const [comparePayload, setComparePayload] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState('');
  const resolvedActiveTab = useMemo(() => {
    if (availableTabs.length === 0) return '';
    if (availableTabs.some((tab) => tab.key === activeTab)) return activeTab;
    return availableTabs[availableTabs.length - 1].key;
  }, [activeTab, availableTabs]);

  useEffect(() => {
    let disposed = false;
    if (!strategyName) {
      setCompareOptions(['latest']);
      return undefined;
    }
    const loadCompareOptions = async () => {
      try {
        const data = await fetchStrategyCompareOptions(strategyName);
        if (disposed) return;
        const options = Array.isArray(data?.versions)
          ? data.versions.filter((item) => typeof item === 'string' && item.trim() !== '')
          : [];
        setCompareOptions(options.length > 0 ? options : ['latest']);
      } catch (err) {
        if (disposed) return;
        setCompareOptions(['latest']);
      }
    };
    loadCompareOptions();
    return () => {
      disposed = true;
    };
  }, [strategyName]);

  useEffect(() => {
    let cancelled = false;
    if (!strategyName || !runId) {
      setRemoteReports({ reports: {}, availableTabs: [] });
      setReportStocks({ enum: [], price: [], capital: [] });
      setReportError('');
      return undefined;
    }
    const loadReports = async () => {
      try {
        setReportError('');
        const data = await fetchStrategyReports(strategyName, runId);
        if (cancelled) return;
        setRemoteReports({
          reports: data?.reports || {},
          availableTabs: data?.available_tabs || [],
        });
      } catch (err) {
        if (cancelled) return;
        setReportError(err?.message || '读取报告摘要失败');
        setRemoteReports({ reports: {}, availableTabs: [] });
      }
    };
    loadReports();
    return () => {
      cancelled = true;
    };
  }, [runId, strategyName]);

  useEffect(() => {
    let cancelled = false;
    if (!strategyName || !runId || !resolvedActiveTab) return undefined;
    const loadStocks = async () => {
      try {
        const data = await fetchStrategyReportStocks(strategyName, runId, resolvedActiveTab, { limit: 10 });
        if (cancelled) return;
        const rows = Array.isArray(data?.rows) ? data.rows : [];
        const mapped = rows.map((row, index) => {
          if (resolvedActiveTab === 'enum') {
            return {
              id: `${row.stock_id}-${index}`,
              stockCode: row.stock_id,
              stockName: row.stock_name,
              opportunities: Number(row.opportunities || 0),
              completionRate: Number(row.completion_rate || 0),
              triggerSpanDays: Number(row.trigger_span_days || 0),
            };
          }
          if (resolvedActiveTab === 'price') {
            return {
              id: `${row.stock_id}-${index}`,
              stockCode: row.stock_id,
              stockName: row.stock_name,
              winRate: Number(row.win_rate || 0),
              roi: Number(row.roi || 0),
              holdDays: Number(row.hold_days || 0),
            };
          }
          return {
            id: `${row.stock_id}-${index}`,
            stockCode: row.stock_id,
            stockName: row.stock_name,
            tradeCount: Number(row.trade_count || 0),
            pnl: Number(row.pnl || 0),
            winRate: Number(row.win_rate || 0),
          };
        });
        setReportStocks((prev) => ({ ...prev, [resolvedActiveTab]: mapped }));
      } catch (err) {
        if (cancelled) return;
        setReportStocks((prev) => ({ ...prev, [resolvedActiveTab]: [] }));
      }
    };
    loadStocks();
    return () => {
      cancelled = true;
    };
  }, [resolvedActiveTab, runId, strategyName]);

  useEffect(() => {
    let cancelled = false;
    if (!compareDialogOpen || !strategyName || !runId || !resolvedActiveTab || !compareVersion) {
      setComparePayload(null);
      setCompareError('');
      setCompareLoading(false);
      return undefined;
    }
    const loadCompare = async () => {
      try {
        setCompareLoading(true);
        setCompareError('');
        const data = await fetchStrategyReportCompare(
          strategyName,
          runId,
          compareVersion,
          resolvedActiveTab,
        );
        if (cancelled) return;
        setComparePayload(data || null);
      } catch (err) {
        if (cancelled) return;
        setCompareError(err?.message || '读取对比报告失败');
        setComparePayload(null);
      } finally {
        if (!cancelled) setCompareLoading(false);
      }
    };
    loadCompare();
    return () => {
      cancelled = true;
    };
  }, [compareDialogOpen, compareVersion, resolvedActiveTab, runId, strategyName]);

  const handleTabChange = (_event, nextValue) => {
    setActiveTab(nextValue);
  };

  const renderReportByTab = (tabKey, reportData, title, options = {}) => {
    if (tabKey === 'enum') {
      return (
        <OpportunityEnumrateReport
          metrics={reportData?.enumMetrics}
          stockRows={reportData?.stockRows}
          title={title}
          showStockGrid={options.showStockGrid !== false}
        />
      );
    }
    if (tabKey === 'price') {
      return (
        <PriceFactorReport
          metrics={reportData?.priceMetrics}
          stockRows={reportData?.stockRows}
          strategyName={strategyName}
          runId={runId}
          title={title}
          showStockGrid={options.showStockGrid !== false}
        />
      );
    }
    if (tabKey === 'capital') {
      return (
        <CapitalAllocationReport
          metrics={reportData?.capitalMetrics}
          stockRows={reportData?.stockRows}
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

    const metricsSource = {
      result: {
        enum: remoteReports?.reports?.enum || executionState?.result?.enum || null,
        price: remoteReports?.reports?.price || executionState?.result?.price || null,
        capital: remoteReports?.reports?.capital || executionState?.result?.capital || null,
      },
    };

    if (resolvedActiveTab === 'enum') {
      const enumMetrics = remoteReports?.reports?.enum?.enumMetrics || buildEnumMetrics(metricsSource);
      if (!enumMetrics) {
        return (
          <Typography variant="body2" color="text.secondary">
            枚举步骤已完成，等待汇总指标（Placeholder：后续接真实枚举 summary）。
          </Typography>
        );
      }
      return renderReportByTab(
        'enum',
        { enumMetrics, stockRows: reportStocks.enum },
        '枚举核心结论（草图）',
      );
    }

    if (resolvedActiveTab === 'price') {
      return renderReportByTab(
        'price',
        {
          priceMetrics: buildPriceMetrics(metricsSource),
          stockRows: reportStocks.price,
        },
        '价格回测报告（草图）',
      );
    }

    return renderReportByTab(
      'capital',
      {
        capitalMetrics: buildCapitalMetrics(metricsSource),
        stockRows: reportStocks.capital,
      },
      '资金模拟报告（草图）',
    );
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
          {reportError ? (
            <Typography variant="caption" color="error">{reportError}</Typography>
          ) : null}
          {renderTabContent()}
          <Divider />
          <Typography variant="caption" color="text.secondary">
            注：报告数据已优先接入 BFF API，暂缺字段时会回退为草图推导值。
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
              options={compareOptions}
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
                    enumMetrics:
                      comparePayload?.base_report?.enumMetrics
                      || remoteReports?.reports?.enum?.enumMetrics
                      || buildEnumMetrics({
                        result: {
                          enum: comparePayload?.base_report
                            || remoteReports?.reports?.enum
                            || executionState?.result?.enum
                            || null,
                        },
                      }),
                    priceMetrics: buildPriceMetrics({
                      result: { price: comparePayload?.base_report || remoteReports?.reports?.price || executionState?.result?.price || null },
                    }),
                    capitalMetrics: buildCapitalMetrics({
                      result: { capital: comparePayload?.base_report || remoteReports?.reports?.capital || executionState?.result?.capital || null },
                    }),
                  },
                  '本次报告',
                  { showStockGrid: false },
                )}
              </Stack>
              <Stack spacing={1}>
                <Typography variant="subtitle2" fontWeight={700}>对比版本结果</Typography>
                {compareLoading ? (
                  <Typography variant="caption" color="text.secondary">正在加载对比结果...</Typography>
                ) : null}
                {compareError ? (
                  <Typography variant="caption" color="error">{compareError}</Typography>
                ) : null}
                {compareVersion
                  ? renderReportByTab(
                    resolvedActiveTab,
                    {
                      enumMetrics:
                        comparePayload?.compare_report?.enumMetrics
                        || buildEnumMetrics({ result: { enum: comparePayload?.compare_report || null } }),
                      priceMetrics: buildPriceMetrics({ result: { price: comparePayload?.compare_report || null } }),
                      capitalMetrics: buildCapitalMetrics({ result: { capital: comparePayload?.compare_report || null } }),
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
