import React from 'react';
import PropTypes from 'prop-types';
import { Loading } from 'ui';
import StrategyDesignBreadcrumbCurrent from './breadcrumbCurrent';
import StrategyDesignMetaBar from './metaBar';
import StrategyDesignMetaDialogs from './metaDialogs';
import { StrategyDesignProvider } from './strategyDesignContext';
import { StrategyDesignWorkbenchProvider, useStrategyDesignWorkbenchContext } from './strategyDesignWorkbenchContext';
import StrategyDesignShell from './strategyDesignShell';
import StrategyDesignStepPage from './strategyDesignStepPage';

function StrategyDesignBody() {
  const wb = useStrategyDesignWorkbenchContext();
  if (wb.isLoadingSettings) {
    return (
      <div className="ntq-page__body strategy-design-shell__body is-loading">
        <Loading variant="page" message="正在加载策略工作台…" style={{ minHeight: '48vh' }} />
      </div>
    );
  }

  return (
    <>
      <StrategyDesignMetaBar />
      <StrategyDesignMetaDialogs />
      <div className="ntq-page__body strategy-design-shell__body">
        <StrategyDesignStepPage />
      </div>
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
