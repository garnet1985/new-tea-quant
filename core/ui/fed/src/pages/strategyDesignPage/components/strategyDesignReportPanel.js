import React, { useMemo } from 'react';
import { Box } from '@mui/material';
import StrategyReportPanel from '../../strategyWorkbenchPage/panels/strategyReportPanel/strategyReportPanel';
import { useStrategyDesignSession } from '../strategyDesignContext';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';

function StrategyDesignReportPanel() {
  const wb = useStrategyDesignWorkbenchContext();
  const { session } = useStrategyDesignSession();

  const executionCompareRecentVersionIds = useMemo(
    () => wb.configVersions.slice(0, 5).map((version) => version.id),
    [wb.configVersions],
  );

  return (
    <Box className="ntq-design-step-report">
      <StrategyReportPanel
        key={`design-report-${wb.strategyName || ''}-${session.panelsResetEpoch}-${wb.activeStep}`}
        strategyName={wb.strategyName}
        executionState={session.executionState}
        executionCompareRecentVersionIds={executionCompareRecentVersionIds}
        configVersions={wb.configVersions}
        workbenchSnapshot={session.workbenchSnapshot}
        showReportCompare={wb.hasOtherVersions}
        lockedTab={wb.activeStep}
        embedded
        onForceEnumerate={wb.forceEnumerate}
      />
    </Box>
  );
}

export default StrategyDesignReportPanel;
