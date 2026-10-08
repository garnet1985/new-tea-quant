import { useEffect, useRef } from 'react';
import { fingerprintSignature } from '../lib/strategySettingsFingerprint';

/**
 * 指纹字段变更时清掉进行中的 run（切步填默认值 / 非指纹字段不触发）。
 * 历史 version 报告保留；胶囊用指纹对比显示「设置已变更」。
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
  const compositeSig = fingerprintSignature(draftSettings);

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
