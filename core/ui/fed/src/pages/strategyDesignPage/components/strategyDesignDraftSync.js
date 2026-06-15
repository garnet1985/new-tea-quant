import { useEffect } from 'react';

/** 将 ``StrategySettingsContainer`` 内 draft 同步到制定策略 workbench（Meta 变更检测等）。 */
function StrategyDesignDraftSync({ draftSettings, onDraftSettingsChange }) {
  useEffect(() => {
    if (typeof onDraftSettingsChange === 'function') {
      onDraftSettingsChange(draftSettings);
    }
  }, [draftSettings, onDraftSettingsChange]);

  return null;
}

export default StrategyDesignDraftSync;
