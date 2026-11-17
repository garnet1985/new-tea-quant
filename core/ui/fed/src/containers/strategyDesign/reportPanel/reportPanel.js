import React, { useCallback, useMemo } from 'react';
import { Tabs } from 'ui';
import { StrategyReportPanel } from 'containers/strategyReport';
import { useStrategyDesignSession } from '../strategyDesignContext';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';
import StrategyDesignAttributeReport from '../attributeReport';
import StrategyDesignRollingReport from '../rollingReport';
import './style.scss';

function StrategyDesignReportPanel() {
  const wb = useStrategyDesignWorkbenchContext();
  const { session } = useStrategyDesignSession();
  const showAttrTabs = Boolean(
    wb.isAppliedSettings && (wb.attributeLastGroupId || wb.attributeBusy),
  );
  const showRollingTab = Boolean(
    wb.isAppliedSettings && (wb.rollingHasReport || wb.rollingBusy),
  );
  const showTabs = showAttrTabs || showRollingTab;

  let viewTab = 'backtest';
  if (showTabs && wb.reportViewTab === 'attribute' && showAttrTabs) viewTab = 'attribute';
  if (showTabs && wb.reportViewTab === 'rolling' && showRollingTab) viewTab = 'rolling';

  const handleTabChange = useCallback((next) => {
    if (typeof wb.setReportViewTab === 'function') {
      wb.setReportViewTab(next);
    }
  }, [wb]);

  const tabItems = useMemo(() => {
    const items = [{ id: 'backtest', label: '回测报告', content: null }];
    if (showAttrTabs) {
      items.push({ id: 'attribute', label: '归因报告', content: null });
    }
    if (showRollingTab) {
      items.push({ id: 'rolling', label: '滚动对照', content: null });
    }
    return items;
  }, [showAttrTabs, showRollingTab]);

  return (
    <section
      className="ntq-design-step-report"
      data-ntq-help={wb.hasPersistedSnapshot ? 'strategy-report' : undefined}
    >
      {showTabs ? (
        <div className="ntq-design-step-report__view-tabs">
          <Tabs
            variant="top"
            gap="none"
            value={viewTab}
            onChange={handleTabChange}
            items={tabItems}
            className="ntq-design-step-report__tabs"
            aria-label="报告视图"
          />
          {viewTab === 'attribute' && wb.attributeLastGroupId ? (
            <span className="ntq-muted ntq-design-step-report__group">
              {`组 #${wb.attributeLastGroupId}`}
            </span>
          ) : null}
        </div>
      ) : null}

      {viewTab === 'rolling' ? (
        <StrategyDesignRollingReport
          payload={wb.rollingReport}
          loading={wb.rollingReportLoading}
          error={wb.rollingError && !wb.rollingBusy ? wb.rollingError : ''}
          busy={wb.rollingBusy}
        />
      ) : viewTab === 'attribute' ? (
        <StrategyDesignAttributeReport
          payload={wb.attributeReport}
          loading={wb.attributeReportLoading}
          error={wb.attrError && !wb.attributeBusy ? wb.attrError : ''}
          busy={wb.attributeBusy}
        />
      ) : (
        <StrategyReportPanel
          key={`design-report-${wb.strategyName || ''}-${session.panelsResetEpoch}-${wb.activeStep}`}
          strategyName={wb.strategyName}
          executionState={session.executionState}
          configVersions={wb.configVersions}
          workbenchSnapshot={session.workbenchSnapshot}
          showReportCompare={wb.hasOtherVersions}
          lockedTab={wb.activeStep}
          embedded
          onForceEnumerate={wb.forceEnumerate}
        />
      )}
    </section>
  );
}

export default StrategyDesignReportPanel;
