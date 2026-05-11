import React, { useEffect, useMemo, useState } from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import RefreshRoundedIcon from '@mui/icons-material/RefreshRounded';
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
import OpportunityEnumrateReport from './reports/OpportunityEnumerateReport';
import PriceFactorReport from './reports/PriceFactorReport';
import CapitalAllocationReport from './reports/CapitalAllocationReport';
import {
  buildCapitalMetrics,
  buildEnumMetrics,
  buildPriceMetrics,
  normalizeEnumMetricsFromSummary,
  normalizePriceMetricsFromSummary,
  REPORT_BLOCK_UNAVAILABLE_ZH,
} from '../../mocks/strategyReportMetrics';
import SettingsJsonDiff from './components/SettingsJsonDiff';
import { useWorkbenchCompareVersionMenu } from '../../workbenchCompareVersionMenu';
import {
  COMPARE_EMPTY_OTHER_VERSION_ZH,
  COMPARE_NO_REPORT_FOR_SNAPSHOT_ZH,
  REPORT_COMPARE_MORE_MENU_VALUE,
  STEP_TABS,
} from './constants/strategyReportConstants';
import { useStrategyReportCompareDialog } from './hooks/useStrategyReportCompareDialog';
import { useStrategyReportRemoteData } from './hooks/useStrategyReportRemoteData';
import './strategyReportPanel.scss';

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
  const runId = executionState?.runId || '';

  /** 仅绑定「本轮会话最近一次跑单完成」的快照 id；草稿变更 reset 后为空，不再回退到工作台选中快照，以免参数已改仍拉旧版 report_ref（404 / 条数不一致） */
  const anchorVersionId = useMemo(() => {
    const run = typeof executionState?.lastCompletedWorkbenchVersionId === 'string'
      ? executionState.lastCompletedWorkbenchVersionId.trim()
      : '';
    return run;
  }, [executionState?.lastCompletedWorkbenchVersionId]);

  const {
    compareDropdownVersionIds,
    compareBaselineMenuLabel,
    renderCompareSelectValue,
  } = useWorkbenchCompareVersionMenu(executionCompareRecentVersionIds, anchorVersionId);

  const reportComparePickerVersions = useMemo(() => {
    const cur = String(anchorVersionId || '').trim();
    const rows = Array.isArray(configVersions) ? configVersions : [];
    if (!cur) return rows;
    return rows.filter((v) => v.id !== cur);
  }, [configVersions, anchorVersionId]);
  let reportComparePickerEmptyHint = '暂无可选版本。';
  if (Array.isArray(configVersions) && configVersions.length > 0) {
    reportComparePickerEmptyHint = '没有其它可对比版本（已排除当前工作台快照）。';
  }

  const [activeTab, setActiveTab] = useState('');

  const {
    remoteReports,
    reportStocks,
    reportError,
    enumRefStatus,
    enumRefRows,
    availableTabs,
    resolvedActiveTab,
  } = useStrategyReportRemoteData({
    strategyName,
    runId,
    anchorVersionId,
    activeTab,
    executionState,
  });

  const {
    compareDialogOpen,
    setCompareDialogOpen,
    compareDialogSubTab,
    setCompareDialogSubTab,
    reportCompareMoreOpen,
    setReportCompareMoreOpen,
    baseSettingsPayload,
    compareWorkbenchSnapshot,
    compareVersion,
    setCompareVersion,
    comparePayload,
    compareError,
    handleReportCompareSelectChange,
    compareResultReport,
    compareSideReportBusy,
  } = useStrategyReportCompareDialog({
    strategyName,
    runId,
    anchorVersionId,
    resolvedActiveTab,
    showReportCompare,
  });

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

  const enumReportRefUrl = useMemo(() => {
    if (enumRefStatus !== 'ok' || !anchorVersionId) return '';
    return `${API_VERSION_PREFIX}/strategy/${encodeURIComponent(strategyName)}/enum/report_ref/${encodeURIComponent(anchorVersionId)}`;
  }, [enumRefStatus, anchorVersionId, strategyName]);

  const handleTabChange = (_event, nextValue) => {
    setActiveTab(nextValue);
  };

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
      if (!reportData?.capitalMetrics) {
        return (
          <Typography {...unavailableTypographyProps}>{unavailableZh}</Typography>
        );
      }
      return (
        <CapitalAllocationReport
          metrics={reportData.capitalMetrics}
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
      let stockGridOverlay = null;
      if (anchorVersionId && enumRefStatus === 'missing' && typeof onForceEnumerate === 'function') {
        stockGridOverlay = (
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
            className="ntq-stock-grid-overlay"
          >
            <Stack spacing={1} alignItems="center">
              <RefreshRoundedIcon className="ntq-stock-grid-overlay__icon" />
              <Typography variant="body2" color="text.secondary">
                此结果需要重新执行步骤才能看到结果，点击重新执行
              </Typography>
            </Stack>
          </Box>
        );
      }
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
                className="ntq-attention-btn"
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
                renderValue={renderCompareSelectValue}
                onChange={handleReportCompareSelectChange}
                className="ntq-report-compare__select"
              >
                <MenuItem value="">{compareBaselineMenuLabel}</MenuItem>
                {compareDropdownVersionIds.map((id) => (
                  <MenuItem key={id} value={id}>{id}</MenuItem>
                ))}
                <MenuItem value={REPORT_COMPARE_MORE_MENU_VALUE}>更多版本…</MenuItem>
              </Select>
            </Stack>
            <Box className="ntq-report-compare">
              <Tabs
                value={compareDialogSubTab}
                onChange={(_e, v) => setCompareDialogSubTab(v)}
                variant="standard"
                className="ntq-report-compare__tabs"
              >
                <Tab label="报告" value="report" />
                <Tab label="设置" value="settings" />
              </Tabs>

              <Box className="ntq-report-compare__panel">
                <Box className="ntq-report-compare__scroll">
                  {compareDialogSubTab === 'report' ? (
                    <Box className="ntq-report-compare__grid">
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
                    <Stack spacing={2} className="ntq-report-compare__settings">
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
                          <Box component="pre" className="ntq-report-compare__pre">
                            {JSON.stringify(baseSettingsPayload.settings, null, 2)}
                          </Box>
                        </Stack>
                      ) : null}

                      {!compareVersion ? (
                        <Box className="ntq-report-compare__hint">
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
          <List dense className="ntq-report-compare__picker-list">
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
              {reportComparePickerEmptyHint}
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
