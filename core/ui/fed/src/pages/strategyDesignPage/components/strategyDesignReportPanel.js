import React from 'react';
import { Box } from '@mui/material';
import StrategyReportPanel from '../../strategyWorkbenchPage/panels/strategyReportPanel/strategyReportPanel';
import { useStrategyDesignSession } from '../strategyDesignContext';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';

function StrategyDesignReportPanel() {
  const wb = useStrategyDesignWorkbenchContext();
  const { session } = useStrategyDesignSession();

  return (
    <Box className="ntq-design-step-report">
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
    </Box>
  );
}

export default StrategyDesignReportPanel;
