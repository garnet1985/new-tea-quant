import React, { useEffect, useMemo, useState } from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
  Typography,
} from '@mui/material';
import { API_VERSION_PREFIX } from '../../../../api/conf/apiConfig';
import OpportunityEnumrateReport from './reports/opportunityEnumerate';
import PriceFactorReport from './reports/priceFactor';
import CapitalAllocationReport from './reports/capitalAllocation';
import {
  buildCapitalMetrics,
  buildEnumMetrics,
  buildPriceMetrics,
  normalizeEnumMetricsFromSummary,
  normalizePriceMetricsFromSummary,
  REPORT_BLOCK_UNAVAILABLE_ZH,
} from '../../mocks/strategyReportMetrics';
import SettingsJsonDiff from './settingsDiffView';
import {
  fetchStrategyReportCompare,
  fetchStrategyReportStocks,
  fetchStrategyReports,
  fetchStrategyStepReportRef,
  fetchStrategyVersionDetail,
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

const REPORT_COMPARE_MORE_MENU_VALUE = '__report_compare_more_versions__';

/** 报告对比弹窗右侧：未选其它快照版本 */
const COMPARE_EMPTY_OTHER_VERSION_ZH = '无可对比结果，请选择不同版本';
/** 报告对比弹窗右侧：已选版本但该 Tab 无可用报告数据 */
const COMPARE_NO_REPORT_FOR_SNAPSHOT_ZH = '无可对比结果，没有可用的报告，请使用相应版本生成报告后再试';

function StrategyReportPanel({
  strategyName,
  executionState,
  /** 与执行面板相同：最近工作台 ``version_id``（新→旧，至多 5） */
  executionCompareRecentVersionIds = [],
  /** 完整版本列表，供「更多版本…」弹窗选择对比快照 */
  configVersions = [],
  workbenchResultReport,
  /** ``{ step: 'enum'|'price'|'capital', tick }``：单步跑完后由工作台页注入，切到对应报告 */
  reportTabFocusRequest = null,
  onForceEnumerate,
  /** 至少两条快照时可对比报告；仅一条时隐藏「对比结果」 */
  showReportCompare = true,
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
  const snapshotCapitalSlot = useMemo(() => {
    const slot = workbenchResultReport?.capital_allocation;
    return slot && typeof slot === 'object' ? slot : null;
  }, [workbenchResultReport]);
  const [reportStocks, setReportStocks] = useState({ enum: [], price: [], capital: [] });
  const [reportError, setReportError] = useState('');
  const [enumRefStatus, setEnumRefStatus] = useState('idle');
  const [enumRefRows, setEnumRefRows] = useState([]);
  const runId = executionState?.runId || '';

  /** 仅绑定「本轮会话最近一次跑单完成」的快照 id；草稿变更 reset 后为空，不再回退到工作台选中快照，以免参数已改仍拉旧版 report_ref（404 / 条数不一致） */
  const anchorVersionId = useMemo(() => {
    const run = typeof executionState?.lastCompletedWorkbenchVersionId === 'string'
      ? executionState.lastCompletedWorkbenchVersionId.trim()
      : '';
    return run;
  }, [executionState?.lastCompletedWorkbenchVersionId]);

  const recentCompareIds = useMemo(() => {
    const raw = Array.isArray(executionCompareRecentVersionIds)
      ? executionCompareRecentVersionIds
      : [];
    return raw
      .map((id) => String(id || '').trim())
      .filter(Boolean)
      .slice(0, 5);
  }, [executionCompareRecentVersionIds]);

  const compareDropdownVersionIds = useMemo(() => {
    const cur = String(anchorVersionId || '').trim();
    if (!cur) return recentCompareIds;
    return recentCompareIds.filter((id) => id !== cur);
  }, [recentCompareIds, anchorVersionId]);

  const compareBaselineMenuLabel = useMemo(() => {
    const cur = String(anchorVersionId || '').trim();
    return cur ? `${cur}（当前版本）` : '—（当前版本）';
  }, [anchorVersionId]);

  const reportComparePickerVersions = useMemo(() => {
    const cur = String(anchorVersionId || '').trim();
    const rows = Array.isArray(configVersions) ? configVersions : [];
    if (!cur) return rows;
    return rows.filter((v) => v.id !== cur);
  }, [configVersions, anchorVersionId]);

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
  /** 对比弹窗内：报告 | 设置 */
  const [compareDialogSubTab, setCompareDialogSubTab] = useState('report');
  const [reportCompareMoreOpen, setReportCompareMoreOpen] = useState(false);
  const [baseSettingsPayload, setBaseSettingsPayload] = useState({
    loading: false,
    error: '',
    settings: null,
  });
  /** 对比侧：``GET …/version/{对比 id}`` 全文（用于报告槽位 + 设置 Tab，避免 SWB-14 占位导致右侧全空） */
  const [compareWorkbenchSnapshot, setCompareWorkbenchSnapshot] = useState({
    loading: false,
    error: '',
    detail: null,
  });

  useEffect(() => {
    if (!showReportCompare && compareDialogOpen) setCompareDialogOpen(false);
  }, [showReportCompare, compareDialogOpen]);

  useEffect(() => {
    if (availableTabs.length === 0) return;
    const keys = availableTabs.map((t) => t.key);
    if (!keys.includes(activeTab)) {
      setActiveTab(keys[0]);
    }
  }, [availableTabs, activeTab]);

  useEffect(() => {
    if (!reportTabFocusRequest || typeof reportTabFocusRequest.step !== 'string') return;
    const step = reportTabFocusRequest.step;
    if (!STEP_TABS.some((t) => t.key === step)) return;
    if (!availableTabs.some((tab) => tab.key === step)) return;
    setActiveTab(step);
  }, [reportTabFocusRequest, availableTabs]);

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
      const available = msg?.stock_ref_available !== false;
      if (
        available
        && raw
        && typeof raw === 'object'
        && Object.keys(raw).length > 0
      ) {
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

  useEffect(() => {
    if (!compareDialogOpen) {
      setCompareDialogSubTab('report');
      setReportCompareMoreOpen(false);
    }
  }, [compareDialogOpen]);

  useEffect(() => {
    if (!compareDialogOpen || compareDialogSubTab !== 'settings' || !strategyName) {
      setBaseSettingsPayload({ loading: false, error: '', settings: null });
      return undefined;
    }
    let cancelled = false;
    const curId = String(anchorVersionId || '').trim();

    if (!curId) {
      setBaseSettingsPayload({ loading: false, error: '', settings: null });
    } else {
      setBaseSettingsPayload((prev) => ({ ...prev, loading: true, error: '' }));
      fetchStrategyVersionDetail(strategyName, curId)
        .then((res) => {
          if (cancelled) return;
          setBaseSettingsPayload({
            loading: false,
            error: '',
            settings: res?.settings ?? null,
          });
        })
        .catch((err) => {
          if (cancelled) return;
          setBaseSettingsPayload({
            loading: false,
            error: err?.message || '读取当前快照设置失败',
            settings: null,
          });
        });
    }

    return () => {
      cancelled = true;
    };
  }, [compareDialogOpen, compareDialogSubTab, strategyName, anchorVersionId]);

  useEffect(() => {
    if (!compareDialogOpen || !strategyName || !String(compareVersion || '').trim()) {
      setCompareWorkbenchSnapshot({ loading: false, error: '', detail: null });
      return undefined;
    }
    let cancelled = false;
    const vid = String(compareVersion).trim();
    setCompareWorkbenchSnapshot((prev) => ({ ...prev, loading: true, error: '' }));
    fetchStrategyVersionDetail(strategyName, vid)
      .then((detail) => {
        if (cancelled) return;
        setCompareWorkbenchSnapshot({ loading: false, error: '', detail });
      })
      .catch((err) => {
        if (cancelled) return;
        setCompareWorkbenchSnapshot({
          loading: false,
          error: err?.message || '读取对比快照失败',
          detail: null,
        });
      });
    return () => {
      cancelled = true;
    };
  }, [compareDialogOpen, compareVersion, strategyName]);

  const handleTabChange = (_event, nextValue) => {
    setActiveTab(nextValue);
  };

  const handleReportCompareSelectChange = (event) => {
    const value = event.target.value;
    const proceed = () => {
      if (value === REPORT_COMPARE_MORE_MENU_VALUE) {
        setReportCompareMoreOpen(true);
        return;
      }
      setCompareVersion(value);
    };
    window.setTimeout(proceed, 0);
  };

  const renderReportCompareSelectValue = (selected) => {
    if (selected === '' || selected == null) return compareBaselineMenuLabel;
    return String(selected);
  };

  const compareResultReport = compareWorkbenchSnapshot.detail?.result_report && typeof compareWorkbenchSnapshot.detail.result_report === 'object'
    ? compareWorkbenchSnapshot.detail.result_report
    : null;

  const compareSideReportBusy = Boolean(
    compareVersion
      && (compareLoading || compareWorkbenchSnapshot.loading),
  );

  /** 对比弹窗内报告区块副标题：仅报告类型，版本号在列头「当前版本（vx）」展示 */
  const compareDialogReportKindLabel = useMemo(() => {
    const row = STEP_TABS.find((t) => t.key === resolvedActiveTab);
    return row?.label ?? '报告';
  }, [resolvedActiveTab]);

  const enumStockRowsForGrid = useMemo(() => {
    if (enumRefStatus === 'ok' && Array.isArray(enumRefRows) && enumRefRows.length > 0) {
      return enumRefRows;
    }
    return reportStocks.enum;
  }, [enumRefRows, enumRefStatus, reportStocks.enum]);

  const renderReportByTab = (tabKey, reportData, title, options = {}) => {
    const unavailableZh = options.unavailableHintZh ?? REPORT_BLOCK_UNAVAILABLE_ZH;
    const unavailableTypographyProps = options.unavailableHintZh
      ? { variant: 'body2', color: 'text.primary' }
      : { variant: 'body2', color: 'text.secondary' };
    if (tabKey === 'enum') {
      if (!reportData?.enumMetrics) {
        return (
          <Typography {...unavailableTypographyProps}>{unavailableZh}</Typography>
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
          <Typography {...unavailableTypographyProps}>{unavailableZh}</Typography>
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

    /** 快照 ``result_report.*`` 须优先于 ``executionState.result.*``：hydration 里 enum/price 仅为卡片摘要，会遮住完整枚举/价格报告字段导致首屏各区「数据异常」。 */
    const metricsSource = {
      result: {
        enum:
          snapshotEnumSlot
          || executionState?.result?.enum
          || remoteReports?.reports?.enum
          || null,
        price:
          snapshotPriceSlot
          || executionState?.result?.price
          || remoteReports?.reports?.price
          || null,
        capital:
          executionState?.result?.capital
          || remoteReports?.reports?.capital
          || null,
        capital_allocation: snapshotCapitalSlot || null,
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
          {showReportCompare ? (
            <Stack direction="row" justifyContent="flex-end">
              <Button
                size="small"
                variant="outlined"
                disabled={!resolvedActiveTab}
                onClick={() => {
                  setCompareDialogSubTab('report');
                  setCompareDialogOpen(true);
                }}
              >
                对比结果
              </Button>
            </Stack>
          ) : null}
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
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
              <Typography variant="caption" color="text.secondary">对比版本</Typography>
              <Select
                size="small"
                displayEmpty
                value={compareVersion}
                renderValue={renderReportCompareSelectValue}
                onChange={handleReportCompareSelectChange}
                sx={{ minWidth: 168 }}
              >
                <MenuItem value="">{compareBaselineMenuLabel}</MenuItem>
                {compareDropdownVersionIds.map((id) => (
                  <MenuItem key={id} value={id}>{id}</MenuItem>
                ))}
                <MenuItem value={REPORT_COMPARE_MORE_MENU_VALUE}>更多版本…</MenuItem>
              </Select>
            </Stack>
            <Box sx={{ width: '100%', display: 'flex', flexDirection: 'column', mt: 0 }}>
              <Tabs
                value={compareDialogSubTab}
                onChange={(_e, v) => setCompareDialogSubTab(v)}
                variant="standard"
                sx={{
                  width: '100%',
                  minHeight: 40,
                  borderBottom: 1,
                  borderColor: 'divider',
                  '& .MuiTabs-flexContainer': { gap: 0.5 },
                  '& .MuiTab-root': {
                    minHeight: 40,
                    minWidth: 'auto',
                    px: 2,
                    py: 1,
                  },
                }}
              >
                <Tab label="报告" value="report" />
                <Tab label="设置" value="settings" />
              </Tabs>

              <Box
                sx={{
                  height: { xs: '58vh', sm: 560 },
                  minHeight: 360,
                  maxHeight: { xs: '72vh', md: 640 },
                  display: 'flex',
                  flexDirection: 'column',
                  overflow: 'hidden',
                  mt: 0,
                  borderLeft: 1,
                  borderRight: 1,
                  borderBottom: 1,
                  borderColor: 'divider',
                  borderTop: 0,
                  borderTopLeftRadius: 0,
                  borderTopRightRadius: 0,
                  borderBottomLeftRadius: 1,
                  borderBottomRightRadius: 1,
                  bgcolor: 'background.paper',
                  p: 1.5,
                }}
              >
              <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto' }}>
                {compareDialogSubTab === 'report' ? (
              <Box
                sx={{
                  display: 'grid',
                  gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
                  gap: 2,
                  alignItems: 'start',
                }}
              >
                <Stack spacing={1}>
                  <Typography variant="body2" color="text.primary">
                    {`当前版本（${anchorVersionId || '—'}）`}
                  </Typography>
                  {renderReportByTab(
                    resolvedActiveTab,
                    {
                      enumMetrics: normalizeEnumMetricsFromSummary(
                        comparePayload?.base_report
                          ?? snapshotEnumSlot
                          ?? executionState?.result?.enum
                          ?? remoteReports?.reports?.enum,
                      ),
                      priceMetrics: normalizePriceMetricsFromSummary(
                        comparePayload?.base_report?.price_factor
                          ?? comparePayload?.base_report
                          ?? snapshotPriceSlot
                          ?? remoteReports?.reports?.price
                          ?? executionState?.result?.price,
                      ),
                      capitalMetrics: buildCapitalMetrics({
                        result: {
                          capital_allocation: comparePayload?.base_report?.capital_allocation
                            ?? snapshotCapitalSlot
                            ?? null,
                          capital: (comparePayload?.base_report && typeof comparePayload.base_report === 'object'
                            && (comparePayload.base_report.profit !== undefined
                              || comparePayload.base_report.initialCapital !== undefined)
                            ? comparePayload.base_report
                            : null)
                            ?? remoteReports?.reports?.capital
                            ?? executionState?.result?.capital
                            ?? null,
                        },
                      }),
                    },
                    compareDialogReportKindLabel,
                    { showStockGrid: false },
                  )}
                </Stack>
                <Stack spacing={1}>
                  <Typography variant="body2" color="text.primary">
                    {`对比版本（${compareVersion || '—'}）`}
                  </Typography>
                  {compareVersion ? (
                    <>
                      {(compareWorkbenchSnapshot.error || compareError) ? (
                        <Typography variant="caption" color="error">
                          {compareWorkbenchSnapshot.error || compareError}
                        </Typography>
                      ) : null}
                      {!(compareWorkbenchSnapshot.error || compareError) && compareSideReportBusy ? (
                        <Typography variant="caption" color="text.secondary">
                          正在加载对比快照…
                        </Typography>
                      ) : null}
                      {!(compareWorkbenchSnapshot.error || compareError) && !compareSideReportBusy
                        ? renderReportByTab(
                          resolvedActiveTab,
                          {
                            enumMetrics: normalizeEnumMetricsFromSummary(
                              comparePayload?.compare_report ?? compareResultReport?.enum,
                            ),
                            priceMetrics: normalizePriceMetricsFromSummary(
                              comparePayload?.compare_report?.price_factor
                                ?? comparePayload?.compare_report
                                ?? compareResultReport?.price_factor,
                            ),
                            capitalMetrics: buildCapitalMetrics({
                              result: {
                                capital_allocation:
                                  comparePayload?.compare_report?.capital_allocation
                                  ?? compareResultReport?.capital_allocation
                                  ?? null,
                                capital:
                                  comparePayload?.compare_report
                                  && typeof comparePayload.compare_report === 'object'
                                  && (comparePayload.compare_report.profit !== undefined
                                    || comparePayload.compare_report.initialCapital !== undefined)
                                    ? comparePayload.compare_report
                                    : null,
                              },
                            }),
                          },
                          compareDialogReportKindLabel,
                          {
                            showStockGrid: false,
                            unavailableHintZh: COMPARE_NO_REPORT_FOR_SNAPSHOT_ZH,
                          },
                        )
                        : null}
                    </>
                  ) : (
                    <Typography variant="body2" color="text.primary">
                      {COMPARE_EMPTY_OTHER_VERSION_ZH}
                    </Typography>
                  )}
                </Stack>
              </Box>
            ) : (
              <Stack spacing={2} sx={{ height: '100%', minHeight: 0 }}>
                {!anchorVersionId ? (
                  <Typography variant="body2" color="text.secondary">
                    暂无绑定工作台快照版本，无法加载当前设置。
                  </Typography>
                ) : null}
                {anchorVersionId && baseSettingsPayload.loading ? (
                  <Typography variant="caption" color="text.secondary">正在加载当前快照设置…</Typography>
                ) : null}
                {baseSettingsPayload.error ? (
                  <Typography variant="caption" color="error">{baseSettingsPayload.error}</Typography>
                ) : null}
                {compareVersion && compareWorkbenchSnapshot.loading ? (
                  <Typography variant="caption" color="text.secondary">正在加载对比快照设置…</Typography>
                ) : null}
                {compareWorkbenchSnapshot.error ? (
                  <Typography variant="caption" color="error">{compareWorkbenchSnapshot.error}</Typography>
                ) : null}

                {anchorVersionId && !baseSettingsPayload.loading && !baseSettingsPayload.error
                && baseSettingsPayload.settings && !compareVersion ? (
                  <Stack spacing={1}>
                    <Typography variant="subtitle2" fontWeight={700}>当前快照 settings</Typography>
                    <Box
                      component="pre"
                      sx={{
                        m: 0,
                        p: 1.5,
                        maxHeight: 420,
                        overflow: 'auto',
                        border: 1,
                        borderColor: 'divider',
                        borderRadius: 1,
                        fontSize: 12,
                        bgcolor: 'action.hover',
                      }}
                    >
                      {JSON.stringify(baseSettingsPayload.settings, null, 2)}
                    </Box>
                  </Stack>
                ) : null}

                {!compareVersion ? (
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
                      选择对比版本后，左右两栏将并排高亮 settings 差异。
                    </Typography>
                  </Box>
                ) : null}

                {compareVersion && anchorVersionId && !baseSettingsPayload.loading && !baseSettingsPayload.error
                && baseSettingsPayload.settings && !compareWorkbenchSnapshot.loading
                && !compareWorkbenchSnapshot.error && compareWorkbenchSnapshot.detail?.settings ? (
                  <SettingsJsonDiff
                    left={baseSettingsPayload.settings}
                    right={compareWorkbenchSnapshot.detail.settings}
                    leftTitle={`当前版本（${anchorVersionId || '—'}）`}
                    rightTitle={`对比版本（${compareVersion || '—'}）`}
                  />
                ) : null}
              </Stack>
                )}
              </Box>
              </Box>
            </Box>
          </Stack>
        </DialogContent>
      </Dialog>

      <Dialog
        open={reportCompareMoreOpen}
        onClose={() => setReportCompareMoreOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>选择对比版本</DialogTitle>
        <DialogContent dividers>
          <List dense sx={{ maxHeight: 360, overflow: 'auto' }}>
            {reportComparePickerVersions.map((version) => (
              <ListItemButton
                key={version.id}
                onClick={() => {
                  setCompareVersion(version.id);
                  setReportCompareMoreOpen(false);
                }}
              >
                <ListItemText
                  primary={version.id}
                  secondary={version.updatedAt || version.createdAt}
                />
              </ListItemButton>
            ))}
          </List>
          {reportComparePickerVersions.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              {(Array.isArray(configVersions) && configVersions.length > 0)
                ? '没有其它可对比版本（已排除当前工作台快照）。'
                : '暂无可选版本。'}
            </Typography>
          ) : null}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReportCompareMoreOpen(false)}>关闭</Button>
        </DialogActions>
      </Dialog>
    </Accordion>
  );
}

export default StrategyReportPanel;
