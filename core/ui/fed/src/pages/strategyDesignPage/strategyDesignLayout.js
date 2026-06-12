import React, { useMemo } from 'react';
import { Box } from '@mui/material';
import { Navigate, Outlet, useParams } from 'react-router-dom';
import {
  getStrategyDesignPath,
  getStrategyDisplayLabel,
} from '../../api/apis/strategyApi';
import StrategyDesignMetaBar from './components/strategyDesignMetaBar';
import StrategyDesignMetaDialogs from './components/strategyDesignMetaDialogs';
import StrategyDesignStepper from './components/strategyDesignStepper';
import { STRATEGY_DESIGN_DEFAULT_STEP } from './constants/strategyDesignSteps';
import { parseStrategyDesignRoute } from './lib/parseStrategyDesignRoute';
import { readCachedStrategyDesignStep } from './strategyDesignSessionState';
import { StrategyDesignProvider } from './strategyDesignContext';
import { StrategyDesignWorkbenchProvider } from './strategyDesignWorkbenchContext';
import StrategyDesignShell from './strategyDesignShell';

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
          <Box className="strategy-design-shell__stepper-wrap">
            <StrategyDesignStepper />
          </Box>
          <StrategyDesignMetaBar />
          <StrategyDesignMetaDialogs />
          <Box className="ntq-page__body strategy-design-shell__body">
            <Outlet />
          </Box>
        </StrategyDesignShell>
      </StrategyDesignWorkbenchProvider>
    </StrategyDesignProvider>
  );
}

export default StrategyDesignLayout;
