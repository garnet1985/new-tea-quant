import React, { useCallback } from 'react';
import { Box, Tab, Tabs, Typography } from '@mui/material';
import { StrategyReportPanel } from 'containers/strategyReport';
import { useStrategyDesignSession } from '../strategyDesignContext';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';
import StrategyDesignAttributeReport from '../attributeReport';
import './style.scss';

function StrategyDesignReportPanel() {
  const wb = useStrategyDesignWorkbenchContext();
  const { session } = useStrategyDesignSession();
  const showAttrTabs = Boolean(wb.attributeVisible);
  const viewTab = showAttrTabs && wb.reportViewTab === 'attribute' ? 'attribute' : 'backtest';

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
      {showAttrTabs ? (
        <Box className="ntq-design-step-report__view-tabs">
          <Tabs
            value={viewTab}
            onChange={handleTabChange}
            variant="standard"
            className="ntq-design-step-report__tabs"
          >
            <Tab value="backtest" label="回测报告" disableRipple />
            <Tab value="attribute" label="归因报告" disableRipple />
          </Tabs>
          {viewTab === 'attribute' && wb.attributeLastGroupId ? (
            <Typography variant="caption" color="text.secondary" className="ntq-design-step-report__group">
              {`组 #${wb.attributeLastGroupId}`}
            </Typography>
          ) : null}
        </Box>
      ) : null}

      {viewTab === 'attribute' ? (
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
