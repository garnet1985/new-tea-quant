import { useEffect, useRef } from 'react';

/**
 * 左侧 settings 草稿变更时重置执行/报告会话（对齐策略实验室 ``WorkbenchDraftChangeResetBridge``）。
 */
function StrategyDesignDraftChangeBridge({
  draftSettings,
  strategyName,
  isLoadingSettings,
  onReset,
  suppressDraftDrivenPanelResetRef,
}) {
  const baselineSigRef = useRef(null);
  const establishedRef = useRef(false);
  const compositeSig = JSON.stringify(draftSettings);

  useEffect(() => {
    if (!strategyName) return;
    if (isLoadingSettings) {
      establishedRef.current = false;
      baselineSigRef.current = null;
      return;
    }
    if (!establishedRef.current) {
      baselineSigRef.current = compositeSig;
      establishedRef.current = true;
      return;
    }
    if (compositeSig !== baselineSigRef.current) {
      baselineSigRef.current = compositeSig;
      if (suppressDraftDrivenPanelResetRef?.current) {
        suppressDraftDrivenPanelResetRef.current = false;
        return;
      }
      onReset();
    }
  }, [
    compositeSig,
    strategyName,
    isLoadingSettings,
    onReset,
    suppressDraftDrivenPanelResetRef,
  ]);

  return null;
}

export default StrategyDesignDraftChangeBridge;
