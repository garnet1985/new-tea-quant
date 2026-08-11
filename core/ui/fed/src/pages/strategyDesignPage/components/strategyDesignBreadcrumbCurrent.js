import React from 'react';
import { resolveStrategyShortLabel } from '../../strategyWorkbenchPage/panels/strategySettingsPanel/editorSchemas/strategyMeta';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';

/** 制定策略面包屑末段：display_name → meta.key → 路径末段 */
function StrategyDesignBreadcrumbCurrent() {
  const wb = useStrategyDesignWorkbenchContext();
  return resolveStrategyShortLabel({
    displayName: wb.strategyDisplayName,
    key: wb.strategyKey,
    name: wb.strategyName,
  });
}

export default StrategyDesignBreadcrumbCurrent;
