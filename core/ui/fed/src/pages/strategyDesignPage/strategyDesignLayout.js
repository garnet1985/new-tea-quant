import React, { useMemo } from 'react';
import { Box } from '@mui/material';
import { Navigate, useParams } from 'react-router-dom';
import {
  getStrategyDesignPath,
  getStrategyDisplayLabel,
} from '../../api/apis/strategyApi';
import StrategyDesignMetaBar from './components/strategyDesignMetaBar';
import StrategyDesignMetaDialogs from './components/strategyDesignMetaDialogs';
import { STRATEGY_DESIGN_DEFAULT_STEP } from './constants/strategyDesignSteps';
import { parseStrategyDesignRoute } from './lib/parseStrategyDesignRoute';
import { readCachedStrategyDesignStep } from './strategyDesignSessionState';
import { StrategyDesignProvider } from './strategyDesignContext';
import { StrategyDesignWorkbenchProvider } from './strategyDesignWorkbenchContext';
import StrategyDesignShell from './strategyDesignShell';
import StrategyDesignStepPage from './strategyDesignStepPage';

/**
 * 制定策略顶层容器：面包屑 + Stepper + 步内 Outlet。
 */
function StrategyDesignLayout() {
  const params = useParams();
  const { strategyName, step } = useMemo(
    () => parseStrategyDesignRoute(params['*']),
    [params],
  );

  if (!strategyName) {
    return <Navigate to="/strategy-design" replace />;
  }

  if (!step) {
    const target = readCachedStrategyDesignStep(strategyName) || STRATEGY_DESIGN_DEFAULT_STEP;
    return <Navigate to={getStrategyDesignPath(strategyName, target)} replace />;
  }

  const displayLabel = getStrategyDisplayLabel({ name: strategyName });

  return (
    <StrategyDesignProvider strategyName={strategyName} initialStep={step}>
      <StrategyDesignWorkbenchProvider>
        <StrategyDesignShell
          breadcrumbsItems={[
            { label: '制定策略', to: '/strategy-design' },
            { label: '选择策略', to: '/strategy-design' },
          ]}
          breadcrumbsCurrent={displayLabel || strategyName}
        >
          <StrategyDesignMetaBar />
          <StrategyDesignMetaDialogs />
          <Box className="ntq-page__body strategy-design-shell__body">
            <StrategyDesignStepPage />
          </Box>
        </StrategyDesignShell>
      </StrategyDesignWorkbenchProvider>
    </StrategyDesignProvider>
  );
}

export default StrategyDesignLayout;
