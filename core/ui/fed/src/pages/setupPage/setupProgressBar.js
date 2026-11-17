import React, { useEffect, useRef } from 'react';
import { ProgressBar } from 'ui';
import { useFakeProgress } from 'service/progress/useFakeProgress';
import {
  fakeProgressTickSize,
  importWithinStepRatio,
  setupFakeProgressBounds,
  setupWeightedPercent,
} from './setup.helpers';
import './setupProgressBar.scss';

function SetupProgressBar({
  definition,
  completedIds,
  runningStepId,
  flowStage,
  importProgress,
  completedCount,
}) {
  const progressPercent = setupWeightedPercent(definition, { completedIds });
  const { capPercent } = setupFakeProgressBounds(definition, {
    completedIds,
    runningStepId,
  });
  const tick = Number(fakeProgressTickSize(progressPercent, capPercent).toFixed(2));
  const displayPercent = useFakeProgress(
    flowStage === 'executing',
    progressPercent,
    { cap: capPercent, step: tick },
  );

  const withinHeldRef = useRef(0);
  const barHeldRef = useRef(0);
  const onImportStep = flowStage === 'executing' && runningStepId === 'import_data';

  useEffect(() => {
    if (!onImportStep) {
      withinHeldRef.current = 0;
    }
  }, [onImportStep]);

  useEffect(() => {
    if (flowStage !== 'executing') {
      barHeldRef.current = 0;
    }
  }, [flowStage]);

  // 下载/导表真实进度；步骤内单调，且不得超过当前步骤假进度上界。
  const rawWithin = onImportStep ? importWithinStepRatio(importProgress) : 0;
  if (onImportStep && importProgress?.running) {
    withinHeldRef.current = Math.max(withinHeldRef.current, rawWithin);
  }
  const within = onImportStep ? withinHeldRef.current : 0;
  const importWeightedPercent = within > 0
    ? setupWeightedPercent(definition, {
      completedIds,
      runningStepId: 'import_data',
      withinStepRatio: within,
    })
    : 0;
  const boundedImportPercent = importWeightedPercent > 0
    ? Math.min(importWeightedPercent, capPercent)
    : 0;

  const candidate = Math.max(displayPercent, boundedImportPercent, progressPercent);
  const boundedCandidate = flowStage === 'executing'
    ? Math.min(candidate, Math.max(capPercent, progressPercent))
    : candidate;

  if (flowStage === 'executing') {
    barHeldRef.current = Math.max(barHeldRef.current, boundedCandidate);
  }

  const shownPercent = flowStage === 'success'
    ? 100
    : flowStage === 'executing'
      ? barHeldRef.current
      : progressPercent;

  return (
    <div className="setup-page__progress">
      <p className="setup-page__progress-meta ntq-muted">
        {`总进度: ${completedCount}/${definition.length} (${Math.round(shownPercent)}%)`}
      </p>
      <ProgressBar
        className="setup-page__progress-bar"
        value={shownPercent}
        size="sm"
        aria-label="安装总进度"
      />
    </div>
  );
}

export default React.memo(SetupProgressBar);
