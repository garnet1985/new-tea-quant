import React from 'react';
import PropTypes from 'prop-types';
import { Box } from '@mui/material';
import PageLoadingState from 'views/pageLoadingState';
import StrategyDesignBreadcrumbCurrent from './components/strategyDesignBreadcrumbCurrent';
import StrategyDesignMetaBar from './components/strategyDesignMetaBar';
import StrategyDesignMetaDialogs from './components/strategyDesignMetaDialogs';
import { StrategyDesignProvider } from './strategyDesignContext';
import { StrategyDesignWorkbenchProvider, useStrategyDesignWorkbenchContext } from './strategyDesignWorkbenchContext';
import StrategyDesignShell from './strategyDesignShell';
import StrategyDesignStepPage from './strategyDesignStepPage';

function StrategyDesignBody() {
  const wb = useStrategyDesignWorkbenchContext();
  if (wb.isLoadingSettings) {
    return (
      <Box className="ntq-page__body strategy-design-shell__body is-loading">
        <PageLoadingState message="正在加载策略工作台…" minHeight="48vh" />
      </Box>
    );
  }

  return (
    <>
      <StrategyDesignMetaBar />
      <StrategyDesignMetaDialogs />
      <Box className="ntq-page__body strategy-design-shell__body">
        <StrategyDesignStepPage />
      </Box>
    </>
  );
}

function StrategyDesign({ strategyName, step }) {
  return (
    <StrategyDesignProvider key={strategyName} strategyName={strategyName} initialStep={step}>
      <StrategyDesignWorkbenchProvider>
        <StrategyDesignShell
          breadcrumbsItems={[
            { label: '制定策略', to: '/strategy-design' },
            { label: '选择策略', to: '/strategy-design' },
          ]}
          breadcrumbsCurrent={<StrategyDesignBreadcrumbCurrent />}
        >
          <StrategyDesignBody />
        </StrategyDesignShell>
      </StrategyDesignWorkbenchProvider>
    </StrategyDesignProvider>
  );
}

StrategyDesign.propTypes = {
  strategyName: PropTypes.string.isRequired,
  step: PropTypes.string.isRequired,
};

export default StrategyDesign;
