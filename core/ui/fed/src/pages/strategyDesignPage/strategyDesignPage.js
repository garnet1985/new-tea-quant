import React, { useMemo } from 'react';
import { Navigate, useLocation, useParams } from 'react-router-dom';
import { getStrategyDesignPath } from 'api/strategyApi';
import StrategyDesign, {
  STRATEGY_DESIGN_DEFAULT_STEP,
  parseStrategyDesignRoute,
  readCachedStrategyDesignStep,
} from 'containers/strategyDesign';

function StrategyDesignPage() {
  const params = useParams();
  const location = useLocation();
  const { strategyName, step } = useMemo(
    () => parseStrategyDesignRoute(params['*']),
    [params],
  );

  if (!strategyName) {
    return <Navigate to="/strategy-design" replace />;
  }

  if (!step) {
    const target = readCachedStrategyDesignStep(strategyName) || STRATEGY_DESIGN_DEFAULT_STEP;
    return (
      <Navigate
        to={getStrategyDesignPath(strategyName, target)}
        replace
        state={location.state}
      />
    );
  }

  return <StrategyDesign strategyName={strategyName} step={step} />;
}

export default StrategyDesignPage;
