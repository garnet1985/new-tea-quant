import React, { useCallback } from 'react';
import { Box, Tab, Tabs, Typography } from '@mui/material';
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

  const handleTabChange = useCallback((_event, next) => {
    if (typeof wb.setReportViewTab === 'function') {
      wb.setReportViewTab(next);
    }
  }, [wb]);

  return (
    <Box
      className="ntq-design-step-report"
      data-ntq-help={wb.hasPersistedSnapshot ? 'strategy-report' : undefined}
    >
      {showTabs ? (
        <Box className="ntq-design-step-report__view-tabs">
          <Tabs
            value={viewTab}
            onChange={handleTabChange}
            variant="standard"
            className="ntq-design-step-report__tabs"
          >
            <Tab value="backtest" label="回测报告" disableRipple />
            {showAttrTabs ? <Tab value="attribute" label="归因报告" disableRipple /> : null}
            {showRollingTab ? <Tab value="rolling" label="滚动对照" disableRipple /> : null}
          </Tabs>
          {viewTab === 'attribute' && wb.attributeLastGroupId ? (
            <Typography variant="caption" color="text.secondary" className="ntq-design-step-report__group">
              {`组 #${wb.attributeLastGroupId}`}
            </Typography>
          ) : null}
        </Box>
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
    </Box>
  );
}

export default StrategyDesignReportPanel;
