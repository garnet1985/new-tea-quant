import React, { useEffect, useMemo, useState } from 'react';
import NtqIcon from 'components/ntqIcon/ntqIcon';
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
import SettingsAccordionTitle from 'components/settingsAccordionTitle/settingsAccordionTitle';
import OpportunityEnumrateReport from './reports/opportunityEnumerateReport';
import PriceFactorReport from './reports/priceFactorReport';
import CapitalAllocationReport from './reports/capitalAllocationReport';
import {
  normalizeCapitalMetricsFromSummary,
  normalizeEnumMetricsFromSummary,
  normalizePriceMetricsFromSummary,
  REPORT_BLOCK_UNAVAILABLE_ZH,
} from '../../mocks/strategyReportMetrics';
import SettingsJsonDiff from './components/settingsJsonDiff';
import InlineLoadingState from 'components/inlineLoadingState/inlineLoadingState';
import { useWorkbenchCompareVersionMenu } from '../../workbenchCompareVersionMenu';
import {
  COMPARE_EMPTY_OTHER_VERSION_ZH,
  COMPARE_NO_REPORT_FOR_SNAPSHOT_ZH,
  REPORT_COMPARE_MORE_MENU_VALUE,
  STEP_TABS,
} from './constants/strategyReportConstants';
import { useStrategyReportCompareDialog } from './hooks/useStrategyReportCompareDialog';
import { useStrategyReportRemoteData } from './hooks/useStrategyReportRemoteData';
import {
  slotFromResultReport,
} from './lib/strategyReportSlotResolve';
import {
  REPORT_PANEL_TITLE,
  REPORT_PANEL_TOOLTIP,
  REPORT_TAB_SECTION_TITLES,
} from './reportSectionMeta';
import BacktestPeriodBanner from './components/backtestPeriodBanner';
import ReportStockDetailView from './components/reportStockDetailView';
import './strategyReportPanel.scss';

function StrategyReportPanel({
  strategyName,
  executionState,
  /** 与执行面板相同：最近工作台 ``version_id``（新→旧，至多 5） */
  executionCompareRecentVersionIds = [],
  /** 完整版本列表，供「更多版本…」弹窗选择对比快照 */
  configVersions = [],
  /** V2-01 / V2-08 工作台快照；执行/报告/对比左侧同源 */
  workbenchSnapshot = null,
  /** ``{ step: 'enum'|'price'|'capital', tick }``：单步跑完后由工作台页注入，切到对应报告 */
  reportTabFocusRequest = null,
  onForceEnumerate,
  /** 至少两条快照时可对比报告；仅一条时隐藏「对比结果」 */
  showReportCompare = true,
}) {
  const activeWorkbenchVersionId = useMemo(
    () => String(workbenchSnapshot?.versionId || '').trim(),
    [workbenchSnapshot],
  );
  const resultReport = workbenchSnapshot?.result_report ?? null;

  const {
    compareDropdownVersionIds,
    compareBaselineMenuLabel,
    renderCompareSelectValue,
  } = useWorkbenchCompareVersionMenu(executionCompareRecentVersionIds, activeWorkbenchVersionId);

  const reportComparePickerVersions = useMemo(() => {
    const cur = activeWorkbenchVersionId;
    const rows = Array.isArray(configVersions) ? configVersions : [];
    if (!cur) return rows;
    return rows.filter((v) => v.id !== cur);
  }, [configVersions, activeWorkbenchVersionId]);
  let reportComparePickerEmptyHint = '暂无可选版本。';
  if (Array.isArray(configVersions) && configVersions.length > 0) {
    reportComparePickerEmptyHint = '没有其它可对比版本（已排除当前工作台快照）。';
  }

  const [activeTab, setActiveTab] = useState('');
  const [selectedStock, setSelectedStock] = useState(null);
  const [reportStockView, setReportStockView] = useState('list');

  const {
    enumRefStatus,
    enumRefRows,
    availableTabs,
    resolvedActiveTab,
  } = useStrategyReportRemoteData({
    strategyName,
    reportVersionId: activeWorkbenchVersionId,
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
    compareVersion,
    setCompareVersion,
    compareError,
    handleReportCompareSelectChange,
    compareSnapshot,
    compareSideReportBusy,
    baseSettings,
    compareSettings,
  } = useStrategyReportCompareDialog({
    strategyName,
    workbenchSnapshot,
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

  const buildMetricsPayloadForTab = (tabKey, { compareResultReport = null } = {}) => {
    const reportSource = compareResultReport ?? resultReport;
    if (tabKey === 'enum') {
      const slot = slotFromResultReport(reportSource, 'enum');
      return { enumMetrics: normalizeEnumMetricsFromSummary(slot), stockRows: enumStockRowsForGrid };
    }
    if (tabKey === 'price') {
      const slot = slotFromResultReport(reportSource, 'price');
      return { priceMetrics: normalizePriceMetricsFromSummary(slot), stockRows: [] };
    }
    const slot = slotFromResultReport(reportSource, 'capital');
    return {
      capitalMetrics: normalizeCapitalMetricsFromSummary(slot),
      stockRows: [],
    };
  };

  const handleTabChange = (_event, nextValue) => {
    setActiveTab(nextValue);
    setReportStockView('list');
    setSelectedStock(null);
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
    return [];
  }, [enumRefRows, enumRefStatus]);

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
          enumRefStockTotal={options.enumRefStockTotal}
          hideTitle={Boolean(options.hideTitle)}
          stockGridLoading={Boolean(options.stockGridLoading)}
          onStockSelect={options.onStockSelect}
          stockLinkEnabled={Boolean(options.stockLinkEnabled)}
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
          title={title}
          showStockGrid={options.showStockGrid !== false}
          hideTitle={Boolean(options.hideTitle)}
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
          hideTitle={Boolean(options.hideTitle)}
        />
      );
    }
    return null;
  };

  const activeTabSectionTitle = REPORT_TAB_SECTION_TITLES[resolvedActiveTab] ?? '';

  const activeReportSlotForPeriod = useMemo(
    () => slotFromResultReport(resultReport, resolvedActiveTab),
    [resultReport, resolvedActiveTab],
  );

  const renderTabContent = () => {
    if (!resolvedActiveTab) {
      return (
        <Typography variant="body2" color="text.secondary">
          先执行任一步，系统会在这里自动新增对应报告 Tab。
        </Typography>
      );
    }

    if (resolvedActiveTab === 'enum') {
      if (reportStockView === 'detail' && selectedStock) {
        return (
          <ReportStockDetailView
            strategyName={strategyName}
            versionId={activeWorkbenchVersionId}
            stock={selectedStock}
            initialStep="enum"
            stepStatus={executionState?.stepStatus || {}}
            onBack={() => {
              setReportStockView('list');
              setSelectedStock(null);
            }}
          />
        );
      }

      let stockGridOverlay = null;
      if (activeWorkbenchVersionId && enumRefStatus === 'missing' && typeof onForceEnumerate === 'function') {
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
              <NtqIcon name="refresh" size={60} className="ntq-stock-grid-overlay__icon" />
              <Typography variant="body2" color="text.secondary">
                此结果需要重新执行步骤才能看到结果，点击重新执行
              </Typography>
            </Stack>
          </Box>
        );
      }
      return renderReportByTab(
        'enum',
        buildMetricsPayloadForTab('enum'),
        REPORT_TAB_SECTION_TITLES.enum,
        {
          stockGridOverlay,
          enumRefStockTotal: enumRefStatus === 'ok' ? enumRefRows.length : undefined,
          stockGridLoading: Boolean(activeWorkbenchVersionId) && enumRefStatus === 'loading',
          hideTitle: true,
          stockLinkEnabled: executionState?.stepStatus?.enum === 'done' && enumRefStatus === 'ok',
          onStockSelect: (row) => {
            setSelectedStock(row);
            setReportStockView('detail');
          },
        },
      );
    }

    if (resolvedActiveTab === 'price') {
      return renderReportByTab(
        'price',
        buildMetricsPayloadForTab('price'),
        REPORT_TAB_SECTION_TITLES.price,
        { hideTitle: true },
      );
    }

    return renderReportByTab(
      'capital',
      buildMetricsPayloadForTab('capital'),
      REPORT_TAB_SECTION_TITLES.capital,
      { hideTitle: true },
    );
  };

  return (
    <Accordion defaultExpanded disableGutters>
      <AccordionSummary expandIcon={<NtqIcon name="expandMore" size={24} />}>
        <SettingsAccordionTitle
          title={REPORT_PANEL_TITLE}
          tooltip={REPORT_PANEL_TOOLTIP}
          context={{ defaultTooltipShine: true }}
        />
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
          {resolvedActiveTab && activeTabSectionTitle && !(reportStockView === 'detail' && selectedStock) ? (
            <Stack
              direction="row"
              alignItems="center"
              spacing={1.5}
              className="ntq-report-section-head"
            >
              <Typography variant="subtitle2" fontWeight={600} className="ntq-report-section-head__title">
                {activeTabSectionTitle}
              </Typography>
              {showReportCompare ? (
                <Button
                  size="small"
                  variant="outlined"
                  className="ntq-attention-btn ntq-report-section-head__compare"
                  onClick={() => {
                    setCompareDialogSubTab('report');
                    setCompareDialogOpen(true);
                  }}
                >
                  对比结果
                </Button>
              ) : null}
            </Stack>
          ) : null}
          {resolvedActiveTab && !(reportStockView === 'detail' && selectedStock) ? (
            <BacktestPeriodBanner slot={activeReportSlotForPeriod} />
          ) : null}
          {renderTabContent()}
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
                          {`当前版本（${activeWorkbenchVersionId || '—'}）`}
                        </Typography>
                        {renderReportByTab(
                          resolvedActiveTab,
                          buildMetricsPayloadForTab(resolvedActiveTab),
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
                            {compareError ? (
                              <Typography variant="caption" color="error">
                                {compareError}
                              </Typography>
                            ) : null}
                            {!compareError && compareSideReportBusy ? (
                              <InlineLoadingState compact block message="正在加载对比报告…" />
                            ) : null}
                            {!compareError && !compareSideReportBusy
                              ? renderReportByTab(
                                resolvedActiveTab,
                                buildMetricsPayloadForTab(resolvedActiveTab, {
                                  compareResultReport: compareSnapshot?.result_report ?? null,
                                }),
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
                      {!activeWorkbenchVersionId ? (
                        <Typography variant="body2" color="text.secondary">
                          暂无绑定工作台快照版本，无法加载当前设置。
                        </Typography>
                      ) : null}
                      {compareVersion && compareSideReportBusy ? (
                        <InlineLoadingState compact row message="正在加载对比快照…" />
                      ) : null}
                      {compareError ? (
                        <Typography variant="caption" color="error">{compareError}</Typography>
                      ) : null}

                      {activeWorkbenchVersionId && baseSettings && !compareVersion ? (
                        <Stack spacing={1}>
                          <Typography variant="subtitle2" fontWeight={700}>当前快照 settings</Typography>
                          <Box component="pre" className="ntq-report-compare__pre">
                            {JSON.stringify(baseSettings, null, 2)}
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

                      {compareVersion && activeWorkbenchVersionId && baseSettings && compareSettings ? (
                        <SettingsJsonDiff
                          left={baseSettings}
                          right={compareSettings}
                          leftTitle={`当前版本（${activeWorkbenchVersionId || '—'}）`}
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
