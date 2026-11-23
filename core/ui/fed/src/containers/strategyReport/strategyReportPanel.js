import React, { useEffect, useMemo, useState } from 'react';
import { Accordion, Button, Dialog, Icon, SettingsAccordionTitle, Tabs, Loading } from 'ui';
import { VersionPickLabel, VersionPickerDialog, lookupVersionById } from 'containers/versionPick';
import OpportunityEnumrateReport from './opportunityEnumerateReport';
import PriceFactorReport from './priceFactorReport';
import CapitalAllocationReport from './capitalAllocationReport';
import {
  normalizeCapitalMetricsFromSummary,
  normalizeEnumMetricsFromSummary,
  normalizePriceMetricsFromSummary,
  REPORT_BLOCK_UNAVAILABLE_ZH,
} from './mocks/strategyReportMetrics';
import SettingsJsonDiff from './settingsJsonDiff';
import {
  COMPARE_EMPTY_OTHER_VERSION_ZH,
  COMPARE_NO_REPORT_FOR_SNAPSHOT_ZH,
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
import BacktestPeriodBanner from './backtestPeriodBanner';
import ReportStockDetailView from './reportStockDetailView';
import './strategyReportPanel.scss';

function StrategyReportPanel({
  strategyName,
  executionState,
  /** 完整版本列表，供版本选择器选择对比快照 */
  configVersions = [],
  /** V2-01 / V2-08 工作台快照；执行/报告/对比左侧同源 */
  workbenchSnapshot = null,
  /** ``{ step: 'enum'|'price'|'portfolio', tick }``：单步跑完后由工作台页注入，切到对应报告 */
  reportTabFocusRequest = null,
  onForceEnumerate,
  /** 至少两条快照时可对比报告；仅一条时隐藏「对比结果」 */
  showReportCompare = true,
  /** 制定策略：固定展示某一 Tab，隐藏 Tab 切换 */
  lockedTab = '',
  /** 制定策略：无 Accordion 外壳，嵌入右侧报告区 */
  embedded = false,
}) {
  const activeWorkbenchVersionId = useMemo(
    () => String(workbenchSnapshot?.versionId || '').trim(),
    [workbenchSnapshot],
  );
  const resultReport = workbenchSnapshot?.result_report ?? null;

  const comparePickerEmptyHint = (Array.isArray(configVersions) && configVersions.length > 0)
    ? '没有其它可对比版本（已排除当前工作台快照）。'
    : '暂无可选版本。';

  const [activeTab, setActiveTab] = useState('');
  const [selectedStock, setSelectedStock] = useState(null);

  const {
    enumRefStatus,
    enumRefRows,
    priceRefStatus,
    priceRefRows,
    availableTabs,
    resolvedActiveTab,
  } = useStrategyReportRemoteData({
    strategyName,
    reportVersionId: activeWorkbenchVersionId,
    activeTab,
    executionState,
    resultReport,
    reportTabFocusRequest,
    lockedTab,
  });

  const {
    compareDialogOpen,
    setCompareDialogOpen,
    compareDialogSubTab,
    setCompareDialogSubTab,
    comparePickerOpen,
    setComparePickerOpen,
    compareVersion,
    setCompareVersion,
    compareError,
    compareSnapshot,
    compareSideReportBusy,
    baseSettings,
    compareSettings,
  } = useStrategyReportCompareDialog({
    strategyName,
    workbenchSnapshot,
    resolvedActiveTab,
    showReportCompare,
    configVersions,
  });

  useEffect(() => {
    if (lockedTab) {
      setActiveTab(lockedTab);
      return;
    }
    if (availableTabs.length === 0) return;
    const keys = availableTabs.map((t) => t.key);
    if (!keys.includes(activeTab)) {
      setActiveTab(keys[0]);
    }
  }, [availableTabs, activeTab, lockedTab]);

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
      return { priceMetrics: normalizePriceMetricsFromSummary(slot), stockRows: priceStockRowsForGrid };
    }
    const slot = slotFromResultReport(reportSource, 'portfolio');
    const stockRows = Array.isArray(slot?.stockRows) ? slot.stockRows : [];
    return {
      capitalMetrics: normalizeCapitalMetricsFromSummary(slot),
      stockRows,
    };
  };

  const handleTabChange = (nextValue) => {
    setActiveTab(nextValue);
    setSelectedStock(null);
  };

  const closeStockDetail = () => {
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

  const priceStockRowsForGrid = useMemo(() => {
    if (priceRefStatus === 'ok' && Array.isArray(priceRefRows) && priceRefRows.length > 0) {
      return priceRefRows;
    }
    return [];
  }, [priceRefRows, priceRefStatus]);

  const unavailableClass = (options) => (
    options.unavailableHintZh
      ? 'ntq-report-panel__hint'
      : 'ntq-report-panel__hint ntq-muted'
  );

  const renderReportByTab = (tabKey, reportData, title, options = {}) => {
    const unavailableZh = options.unavailableHintZh ?? REPORT_BLOCK_UNAVAILABLE_ZH;
    if (tabKey === 'enum') {
      if (!reportData?.enumMetrics) {
        return <p className={unavailableClass(options)}>{unavailableZh}</p>;
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
        return <p className={unavailableClass(options)}>{unavailableZh}</p>;
      }
      return (
        <PriceFactorReport
          metrics={reportData.priceMetrics}
          stockRows={reportData.stockRows}
          title={title}
          showStockGrid={options.showStockGrid !== false}
          stockGridOverlay={options.stockGridOverlay}
          priceRefStockTotal={options.priceRefStockTotal}
          stockGridLoading={Boolean(options.stockGridLoading)}
          hideTitle={Boolean(options.hideTitle)}
          onStockSelect={options.onStockSelect}
          stockLinkEnabled={Boolean(options.stockLinkEnabled)}
        />
      );
    }
    if (tabKey === 'portfolio') {
      if (!reportData?.capitalMetrics) {
        return <p className={unavailableClass(options)}>{unavailableZh}</p>;
      }
      return (
        <CapitalAllocationReport
          metrics={reportData.capitalMetrics}
          stockRows={reportData?.stockRows}
          title={title}
          showStockGrid={options.showStockGrid !== false}
          showTradeChart={options.showTradeChart !== false}
          hideTitle={Boolean(options.hideTitle)}
        />
      );
    }
    return null;
  };

  const activeTabSectionTitle = REPORT_TAB_SECTION_TITLES[resolvedActiveTab] ?? '';

  const embeddedPanelTitle = useMemo(() => {
    const lt = String(lockedTab || '').trim();
    if (lt && REPORT_TAB_SECTION_TITLES[lt]) return REPORT_TAB_SECTION_TITLES[lt];
    return REPORT_PANEL_TITLE;
  }, [lockedTab]);

  const showSectionHead = Boolean(
    resolvedActiveTab
    && activeTabSectionTitle
    && !(embedded && lockedTab),
  );

  const activeReportSlotForPeriod = useMemo(
    () => slotFromResultReport(resultReport, resolvedActiveTab),
    [resultReport, resolvedActiveTab],
  );

  const tabItems = useMemo(
    () => availableTabs.map((tab) => ({
      id: tab.key,
      label: tab.label,
      content: null,
    })),
    [availableTabs],
  );

  const compareTabItems = useMemo(() => ([
    { id: 'report', label: '报告', content: null },
    { id: 'settings', label: '设置', content: null },
  ]), []);

  const renderTabContent = () => {
    if (lockedTab && executionState?.stepStatus?.[lockedTab] !== 'done') {
      return (
        <p className="ntq-report-panel__hint ntq-muted">
          在上方执行面板点击“开始模拟”来产出报告
        </p>
      );
    }

    if (!resolvedActiveTab) {
      return (
        <p className="ntq-report-panel__hint ntq-muted">
          先执行任一步，系统会在这里自动新增对应报告页签。
        </p>
      );
    }

    if (resolvedActiveTab === 'enum') {
      let stockGridOverlay = null;
      if (activeWorkbenchVersionId && enumRefStatus === 'missing' && typeof onForceEnumerate === 'function') {
        stockGridOverlay = (
          <div
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
            <div className="ntq-stock-grid-overlay__inner">
              <Icon name="refresh" size="xl" className="ntq-stock-grid-overlay__icon" />
              <p className="ntq-report-panel__hint ntq-muted">
                需重新执行本步后才能查看逐股明细，点击重新执行
              </p>
            </div>
          </div>
        );
      } else if (activeWorkbenchVersionId && enumRefStatus === 'error') {
        stockGridOverlay = (
          <div className="ntq-stock-grid-overlay ntq-stock-grid-overlay--static">
            <div className="ntq-stock-grid-overlay__inner">
              <p className="ntq-report-panel__hint ntq-report-panel__hint--error">
                逐股明细加载失败（网络或服务异常），请稍后重试。
              </p>
            </div>
          </div>
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
          },
        },
      );
    }

    if (resolvedActiveTab === 'price') {
      return renderReportByTab(
        'price',
        buildMetricsPayloadForTab('price'),
        REPORT_TAB_SECTION_TITLES.price,
        {
          hideTitle: true,
          priceRefStockTotal: priceRefStatus === 'ok' ? priceRefRows.length : undefined,
          stockGridLoading: Boolean(activeWorkbenchVersionId) && priceRefStatus === 'loading',
          stockLinkEnabled: executionState?.stepStatus?.price === 'done' && priceRefStatus === 'ok',
          onStockSelect: (row) => {
            setSelectedStock(row);
          },
        },
      );
    }

    return renderReportByTab(
      'portfolio',
      buildMetricsPayloadForTab('portfolio'),
      REPORT_TAB_SECTION_TITLES.portfolio,
      { hideTitle: true },
    );
  };

  const reportPanelBody = (
    <div className={[
      'ntq-report-panel__body',
      embedded ? 'ntq-report-panel__embedded-body' : '',
    ].filter(Boolean).join(' ')}
    >
      {!lockedTab && availableTabs.length > 0 ? (
        <Tabs
          className="ntq-report-panel__tabs ntq-tabs--list-only"
          gap="sm"
          value={resolvedActiveTab}
          onChange={handleTabChange}
          items={tabItems}
        />
      ) : null}
      {showSectionHead ? (
        <div className="ntq-report-section-head">
          <h3 className="ntq-report-section-head__title">
            {activeTabSectionTitle}
          </h3>
          {showReportCompare ? (
            <Button
              variant="attention"
              className="ntq-report-section-head__compare"
              onClick={() => {
                setCompareDialogSubTab('report');
                setCompareDialogOpen(true);
              }}
            >
              对比结果
            </Button>
          ) : null}
        </div>
      ) : null}
      {resolvedActiveTab ? (
        <BacktestPeriodBanner slot={activeReportSlotForPeriod} />
      ) : null}
      {renderTabContent()}
      <ReportStockDetailView
        open={Boolean(selectedStock)}
        strategyName={strategyName}
        versionId={activeWorkbenchVersionId}
        stock={selectedStock}
        initialStep={resolvedActiveTab === 'price' ? 'price' : 'enum'}
        stepStatus={executionState?.stepStatus || {}}
        onClose={closeStockDetail}
      />
    </div>
  );

  const reportPanelDialogs = (
    <>
      <Dialog
        open={compareDialogOpen}
        onClose={() => setCompareDialogOpen(false)}
        fullScreen
        className="ntq-report-compare-dialog"
        title={(
          <span className="ntq-report-compare-dialog__title">
            <span className="ntq-report-compare-dialog__title-text">报告对比</span>
            <Button
              variant="ghost"
              icon="close"
              aria-label="关闭"
              onClick={() => setCompareDialogOpen(false)}
            />
          </span>
        )}
      >
        <div className="ntq-report-compare-dialog__body">
          <div className="ntq-report-compare__picker-row">
            <span className="ntq-caption ntq-muted">对比版本</span>
            <Button
              variant="glass"
              className="ntq-report-compare__picker-trigger"
              onClick={() => setComparePickerOpen(true)}
            >
              {compareVersion
                ? <VersionPickLabel version={lookupVersionById(configVersions, compareVersion)} />
                : '选择对比版本'}
            </Button>
          </div>
          <div className="ntq-report-compare">
            <Tabs
              className="ntq-report-compare__tabs ntq-tabs--list-only"
              gap="sm"
              value={compareDialogSubTab}
              onChange={setCompareDialogSubTab}
              items={compareTabItems}
            />

            <div className="ntq-report-compare__panel">
              <div className="ntq-report-compare__scroll">
                {compareDialogSubTab === 'report' ? (
                  <div className="ntq-report-compare__grid">
                    <div className="ntq-report-compare__col">
                      <p className="ntq-report-compare__col-title">
                        {`当前版本（${activeWorkbenchVersionId || '—'}）`}
                      </p>
                      {renderReportByTab(
                        resolvedActiveTab,
                        buildMetricsPayloadForTab(resolvedActiveTab),
                        compareDialogReportKindLabel,
                        { showStockGrid: false, showTradeChart: false },
                      )}
                    </div>
                    <div className="ntq-report-compare__col">
                      <p className="ntq-report-compare__col-title">
                        {`对比版本（${compareVersion || '—'}）`}
                      </p>
                      {compareVersion ? (
                        <>
                          {compareError ? (
                            <p className="ntq-caption ntq-report-panel__hint--error">{compareError}</p>
                          ) : null}
                          {!compareError && compareSideReportBusy ? (
                            <Loading variant="inline" message="正在加载对比报告…" className="is-block" />
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
                                showTradeChart: false,
                                unavailableHintZh: COMPARE_NO_REPORT_FOR_SNAPSHOT_ZH,
                              },
                            )
                            : null}
                        </>
                      ) : (
                        <p className="ntq-report-panel__hint">
                          {COMPARE_EMPTY_OTHER_VERSION_ZH}
                        </p>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="ntq-report-compare__settings">
                    {!activeWorkbenchVersionId ? (
                      <p className="ntq-report-panel__hint ntq-muted">
                        暂无绑定工作台快照版本，无法加载当前设置。
                      </p>
                    ) : null}
                    {compareVersion && compareSideReportBusy ? (
                      <Loading variant="inlineRow" message="正在加载对比快照…" />
                    ) : null}
                    {compareError ? (
                      <p className="ntq-caption ntq-report-panel__hint--error">{compareError}</p>
                    ) : null}

                    {activeWorkbenchVersionId && baseSettings && !compareVersion ? (
                      <div className="ntq-report-compare__settings-block">
                        <h4 className="ntq-report-compare__settings-heading">当前快照配置</h4>
                        <pre className="ntq-report-compare__pre">
                          {JSON.stringify(baseSettings, null, 2)}
                        </pre>
                      </div>
                    ) : null}

                    {!compareVersion ? (
                      <div className="ntq-report-compare__hint">
                        <p className="ntq-report-panel__hint ntq-muted">
                          选择对比版本后，左右两栏将并排高亮配置差异。
                        </p>
                      </div>
                    ) : null}

                    {compareVersion && activeWorkbenchVersionId && baseSettings && compareSettings ? (
                      <SettingsJsonDiff
                        left={baseSettings}
                        right={compareSettings}
                        leftTitle={`当前版本（${activeWorkbenchVersionId || '—'}）`}
                        rightTitle={`对比版本（${compareVersion || '—'}）`}
                      />
                    ) : null}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </Dialog>

      <VersionPickerDialog
        open={comparePickerOpen}
        onClose={() => setComparePickerOpen(false)}
        title="选择对比版本"
        versions={configVersions}
        selectedId={compareVersion}
        excludeIds={activeWorkbenchVersionId ? [activeWorkbenchVersionId] : []}
        emptyHint={comparePickerEmptyHint}
        allowClear={Boolean(compareVersion)}
        clearLabel="不对比"
        onSelect={setCompareVersion}
        dialogSx={{ zIndex: (theme) => theme.zIndex.modal + 2 }}
      />
    </>
  );

  if (embedded) {
    return (
      <div className="ntq-report-panel ntq-report-panel--embedded">
        <div className="ntq-report-panel__embedded-head">
          <SettingsAccordionTitle
            title={embeddedPanelTitle}
            tooltip={REPORT_PANEL_TOOLTIP}
            context={{ defaultTooltipShine: true }}
          />
          {showReportCompare && lockedTab ? (
            <Button
              variant="attention"
              className="ntq-report-panel__embedded-compare"
              data-ntq-help="strategy-report-compare"
              onClick={() => {
                setCompareDialogSubTab('report');
                setCompareDialogOpen(true);
              }}
            >
              对比结果
            </Button>
          ) : null}
        </div>
        {reportPanelBody}
        {reportPanelDialogs}
      </div>
    );
  }

  return (
    <>
      <Accordion
        title={REPORT_PANEL_TITLE}
        tooltip={REPORT_PANEL_TOOLTIP}
        shine
        defaultExpanded
      >
        {reportPanelBody}
      </Accordion>
      {reportPanelDialogs}
    </>
  );
}

export default StrategyReportPanel;
