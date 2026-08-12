import React from 'react';
import { resolveStrategyShortLabel } from '../../strategyWorkbenchPage/panels/strategySettingsPanel/editorSchemas/strategyMeta';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';

/**
 * 制定策略面包屑末段。
 * 优先 display_name / key（含列表导航 state 与 session 种子）；
 * settings 加载中且尚无短名时不回退路径，避免闪一下长路径。
 */
function StrategyDesignBreadcrumbCurrent() {
  const wb = useStrategyDesignWorkbenchContext();
  const hasShortLabel = Boolean(
    String(wb.strategyDisplayName || '').trim()
    || String(wb.strategyKey || '').trim(),
  );

  if (wb.isLoadingSettings && !hasShortLabel) {
    return '\u00A0';
  }

  return resolveStrategyShortLabel({
    displayName: wb.strategyDisplayName,
    key: wb.strategyKey,
    // 仅在 settings 已就绪后才允许路径末段兜底
    name: wb.isLoadingSettings ? '' : wb.strategyName,
  });
}

export default StrategyDesignBreadcrumbCurrent;
