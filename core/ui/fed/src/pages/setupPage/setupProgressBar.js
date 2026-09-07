import React from 'react';
import { Box, Typography } from '@mui/material';
import { useFakeProgress } from '../../hooks/useFakeProgress';
import {
  fakeProgressTickSize,
  setupFakeProgressBounds,
  setupWeightedPercent,
} from './setup.helpers';

function SetupProgressBar({
  definition,
  completedIds,
  runningStepId,
  flowStage,
  importProgress,
  completedCount,
}) {
  const progressPercent = setupWeightedPercent(definition, { completedIds });
  const { capPercent } = setupFakeProgressBounds(definition, {
    completedIds,
    runningStepId,
  });
  const tick = Number(fakeProgressTickSize(progressPercent, capPercent).toFixed(2));
  const displayPercent = useFakeProgress(
    flowStage === 'executing',
    progressPercent,
    { cap: capPercent, step: tick },
  );
  const importWeightedPercent = runningStepId === 'import_data' && importProgress.totalTables > 0
    ? setupWeightedPercent(definition, {
      completedIds,
      runningStepId: 'import_data',
      withinStepRatio: Number(importProgress.percent || 0) / 100,
    })
    : 0;
  const shownPercent = flowStage === 'success'
    ? 100
    : Math.max(displayPercent, importWeightedPercent);

  return (
    <>
      <Typography variant="body2" color="text.secondary">
        总进度: {completedCount}/{definition.length} ({Math.round(shownPercent)}%)
      </Typography>
      <Box className="setup-page__progress-track">
        <Box
          className="setup-page__progress-fill"
          sx={{ width: `${shownPercent}%`, bgcolor: 'primary.main' }}
        />
      </Box>
    </>
  );
}

export default React.memo(SetupProgressBar);
