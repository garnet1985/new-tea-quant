import React from 'react';
import { Box } from '@mui/material';

/** 制定策略步内页占位；后续替换为 Meta 条 + settings | report */
function StrategyDesignStepPlaceholder() {
  return (
    <Box
      className="strategy-design-step-placeholder"
      sx={{
        minHeight: 480,
        border: 1,
        borderColor: 'divider',
        borderRadius: 1,
        backgroundColor: 'background.paper',
      }}
    />
  );
}

export default StrategyDesignStepPlaceholder;
