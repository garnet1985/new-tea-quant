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
import { API_VERSION_PREFIX } from '../../../../api/conf/apiConfig';
import OpportunityEnumrateReport from './reports/opportunityEnumerate';
import PriceFactorReport from './reports/priceFactor';
import CapitalAllocationReport from './reports/capitalAllocation';
import CompareVersionSelect from 'components/compareVersionSelect/compareVersionSelect';
import {
  buildCapitalMetrics,
  buildEnumMetrics,
  buildPriceMetrics,
  normalizeEnumMetricsFromSummary,
  normalizePriceMetricsFromSummary,
  REPORT_BLOCK_UNAVAILABLE_ZH,
} from '../../mocks/strategyReportMetrics';
import {
  fetchStrategyReportCompare,
  fetchStrategyReportStocks,
  fetchStrategyReports,
  fetchStrategyStepReportRef,
} from '../../../../api/apis/strategyApi';

/** 与 ``sortMappedEnumRows`` 字段一致；仅用于首屏默认顺序（后续排序为 DataGrid 客户端） */
const ENUM_REF_DEFAULT_SORT = { sortBy: 'opportunities', order: 'desc' };

function mapStockRefToRows(stockRef) {
  if (!stockRef || typeof stockRef !== 'object') return [];
  return Object.entries(stockRef).map(([code, v]) => {
    const row = v && typeof v === 'object' ? v : {};
    const opp = row.opportunities ?? row.opportunity_count ?? row.opportunityCount;
    return {
      id: String(code),
      stockCode: String(code),
      stockName: String(row.stock_name || row.stockName || code),
      opportunities: Number(opp ?? 0),
      completionRate: Number(row.completion_rate ?? row.completionRate ?? 0),
      triggerSpanDays: Number(row.avg_opportunity_interval_days ?? row.triggerSpanDays ?? 0),
    };
  });
}

/** JSON object 键顺序不可靠：映射成行数组后按维度排序一次，便于首屏与分页。 */
function sortMappedEnumRows(rows, sortBy, order) {
  if (!Array.isArray(rows) || rows.length <= 1) return rows;
  const desc = order === 'desc';
  const tie = (a, b) => String(a.stockCode).localeCompare(String(b.stockCode), undefined, { numeric: true });
  return [...rows].sort((a, b) => {
    let cmp = 0;
    switch (sortBy) {
      case 'stock_code':
        cmp = String(a.stockCode).localeCompare(String(b.stockCode), undefined, { numeric: true });
        break;
      case 'stock_name':
        cmp = String(a.stockName).localeCompare(String(b.stockName), undefined, { numeric: true });
        break;
      case 'completion_rate':
        cmp = Number(a.completionRate) - Number(b.completionRate);
        break;
      case 'avg_opportunity_interval_days':
        cmp = Number(a.triggerSpanDays) - Number(b.triggerSpanDays);
        break;
      case 'opportunities':
      default:
        cmp = Number(a.opportunities) - Number(b.opportunities);
        break;
    }
    if (cmp !== 0) return desc ? -cmp : cmp;
    return tie(a, b);
  });
}

const STEP_TABS = [
  { key: 'enum', label: '枚举报告' },
  { key: 'price', label: '价格回测报告' },
  { key: 'capital', label: '资金模拟报告' },
];

function StrategyReportPanel({
  strategyName,
  executionState,
  compareVersionOptions,
  workbenchResultReport,
  workbenchVersionId = '',
  onForceEnumerate,
}) {
  const [remoteReports, setRemoteReports] = useState({ reports: {}, availableTabs: [] });
  /** V2-01 ``result_report.enum``：含 ``enumMetrics.opportunityCount*``，由页面 ``GET …/version/latest`` 注入 */
  const snapshotEnumSlot = useMemo(() => {
    const slot = workbenchResultReport?.enum;
    return slot && typeof slot === 'object' ? slot : null;
  }, [workbenchResultReport]);
  /** ``result_report.price_factor``：与 ``0_session_summary.json`` / DbCache 写入形态一致（snake_case 汇总） */
  const snapshotPriceSlot = useMemo(() => {
    const slot = workbenchResultReport?.price_factor;
    return slot && typeof slot === 'object' ? slot : null;
  }, [workbenchResultReport]);
  const compareOptions = useMemo(
    () => (
      Array.isArray(compareVersionOptions) && compareVersionOptions.length > 0
        ? compareVersionOptions
        : ['latest']
    ),
    [compareVersionOptions],
  );
  const [reportStocks, setReportStocks] = useState({ enum: [], price: [], capital: [] });
  const [reportError, setReportError] = useState('');
  const [enumRefStatus, setEnumRefStatus] = useState('idle');
  const [enumRefRows, setEnumRefRows] = useState([]);
  const runId = executionState?.runId || '';

  const anchorVersionId = useMemo(() => {
    const run = typeof executionState?.lastCompletedWorkbenchVersionId === 'string'
      ? executionState.lastCompletedWorkbenchVersionId.trim()
      : '';
    if (run) return run;
    const wb = typeof workbenchVersionId === 'string' ? workbenchVersionId.trim() : '';
    return wb && wb !== 'userspace' ? wb : '';
  }, [executionState?.lastCompletedWorkbenchVersionId, workbenchVersionId]);

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

  useEffect(() => {
    if (availableTabs.length === 0) return;
    const keys = availableTabs.map((t) => t.key);
    if (!keys.includes(activeTab)) {
      setActiveTab(keys[0]);
    }
  }, [availableTabs, activeTab]);

  const [compareVersion, setCompareVersion] = useState('');
  const [comparePayload, setComparePayload] = useState(null);
  const [compareLoading, setCompareLoading] = useState(false);
  const [compareError, setCompareError] = useState('');
  const resolvedActiveTab = useMemo(() => {
    if (availableTabs.length === 0) return '';
    if (availableTabs.some((tab) => tab.key === activeTab)) return activeTab;
    return availableTabs[availableTabs.length - 1].key;
  }, [activeTab, availableTabs]);

  const enumReportRefUrl = useMemo(() => {
    if (enumRefStatus !== 'ok' || !anchorVersionId) return '';
    return `${API_VERSION_PREFIX}/strategy/${encodeURIComponent(strategyName)}/enum/report_ref/${encodeURIComponent(anchorVersionId)}`;
  }, [enumRefStatus, anchorVersionId, strategyName]);

  useEffect(() => {
    let cancelled = false;
    if (!strategyName || !anchorVersionId || resolvedActiveTab !== 'enum') {
      setEnumRefStatus('idle');
      setEnumRefRows([]);
      return undefined;
    }
    setEnumRefStatus('loading');
    fetchStrategyStepReportRef(strategyName, 'enum', anchorVersionId).then((msg) => {
      if (cancelled) return;
      const raw = msg?.stock_ref;
      if (raw && typeof raw === 'object' && Object.keys(raw).length > 0) {
        const mapped = sortMappedEnumRows(
          mapStockRefToRows(raw),
          ENUM_REF_DEFAULT_SORT.sortBy,
          ENUM_REF_DEFAULT_SORT.order,
        );
        setEnumRefRows(mapped);
        setEnumRefStatus('ok');
        return;
      }
      setEnumRefRows([]);
      setEnumRefStatus('missing');
    });
    return () => {
      cancelled = true;
    };
  }, [anchorVersionId, resolvedActiveTab, strategyName]);

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

  const enumStockRowsForGrid = useMemo(() => {
    if (enumRefStatus === 'ok' && Array.isArray(enumRefRows) && enumRefRows.length > 0) {
      return enumRefRows;
    }
    return reportStocks.enum;
  }, [enumRefRows, enumRefStatus, reportStocks.enum]);

  const renderReportByTab = (tabKey, reportData, title, options = {}) => {
    if (tabKey === 'enum') {
      if (!reportData?.enumMetrics) {
        return (
          <Typography variant="body2" color="text.secondary">
            {REPORT_BLOCK_UNAVAILABLE_ZH}
          </Typography>
        );
      }
      return (
        <OpportunityEnumrateReport
          metrics={reportData.enumMetrics}
          stockRows={reportData.stockRows}
          title={title}
          showStockGrid={options.showStockGrid !== false}
          stockGridOverlay={options.stockGridOverlay}
          reportRefUrl={options.reportRefUrl || ''}
          enumRefStockTotal={options.enumRefStockTotal}
          stockGridLoading={Boolean(options.stockGridLoading)}
        />
      );
    }
    if (tabKey === 'price') {
      if (!reportData?.priceMetrics) {
        return (
          <Typography variant="body2" color="text.secondary">
            {REPORT_BLOCK_UNAVAILABLE_ZH}
          </Typography>
        );
      }
      return (
        <PriceFactorReport
          metrics={reportData.priceMetrics}
          stockRows={reportData.stockRows}
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
        enum:
          snapshotEnumSlot
          || remoteReports?.reports?.enum
          || executionState?.result?.enum
          || null,
        price:
          snapshotPriceSlot
          || remoteReports?.reports?.price
          || executionState?.result?.price
          || null,
        capital: remoteReports?.reports?.capital || executionState?.result?.capital || null,
      },
    };

    if (resolvedActiveTab === 'enum') {
      const stockGridOverlay =
        anchorVersionId
        && enumRefStatus === 'missing'
        && typeof onForceEnumerate === 'function' ? (
          <Box
            role="button"
            tabIndex={0}
            onClick={() => onForceEnumerate()}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onForceEnumerate();
              }
            }}
            sx={{
              position: 'absolute',
              inset: 0,
              zIndex: 2,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              p: 2,
              borderRadius: 1,
              backgroundColor: 'rgba(255,255,255,0.92)',
              border: 1,
              borderColor: 'divider',
              cursor: 'pointer',
              textAlign: 'center',
            }}
          >
            <Typography variant="body2" color="text.secondary">
              当前快照下没有逐股引用文件；请重新执行枚举（忽略缓存）后查看样本表。点击此处强制执行。
            </Typography>
          </Box>
          ) : null;
      return renderReportByTab(
        'enum',
        { enumMetrics: buildEnumMetrics(metricsSource), stockRows: enumStockRowsForGrid },
        '枚举核心结论',
        {
          stockGridOverlay,
          reportRefUrl: enumReportRefUrl,
          enumRefStockTotal: enumRefStatus === 'ok' ? enumRefRows.length : undefined,
          stockGridLoading: Boolean(anchorVersionId) && enumRefStatus === 'loading',
        },
      );
    }

    if (resolvedActiveTab === 'price') {
      return renderReportByTab(
        'price',
        {
          priceMetrics: buildPriceMetrics(metricsSource),
          stockRows: reportStocks.price,
        },
        '价格回测报告',
      );
    }

    return renderReportByTab(
      'capital',
      {
        capitalMetrics: buildCapitalMetrics(metricsSource),
        stockRows: reportStocks.capital,
      },
      '资金模拟报告',
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
            注：枚举汇总仅使用快照返回字段，缺项的区块会单独提示。价格/资金等报告在数据未齐时可能仍含占位内容。
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
                    enumMetrics: normalizeEnumMetricsFromSummary(
                      comparePayload?.base_report
                        || remoteReports?.reports?.enum
                        || executionState?.result?.enum,
                    ),
                    priceMetrics: normalizePriceMetricsFromSummary(
                      comparePayload?.base_report?.price_factor
                        || comparePayload?.base_report
                        || remoteReports?.reports?.price
                        || executionState?.result?.price,
                    ),
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
                      enumMetrics: normalizeEnumMetricsFromSummary(comparePayload?.compare_report),
                      priceMetrics: normalizePriceMetricsFromSummary(
                        comparePayload?.compare_report?.price_factor || comparePayload?.compare_report,
                      ),
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
