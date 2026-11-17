import React, { useMemo } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Button, Heading, Message } from 'ui';
import StrategyMetaDetailText from '../strategyMetaDetailText';
import { getStrategyListPath } from 'containers/strategyCategory';
import { formatGoalSummaryLines, resolveStrategyShortLabel } from 'containers/strategySettings';
import { STRATEGY_DESIGN_STEP_INTRO } from '../constants/strategyDesignSteps';
import { useStrategyDesignWorkbenchContext } from '../strategyDesignWorkbenchContext';
import StrategyDesignStepper from '../stepper';
import './style.scss';

function MetaFlash({ status, children }) {
  if (!children) return null;
  return (
    <Message status={status} variant="inline" className="ntq-design-meta__flash">
      {children}
    </Message>
  );
}

function StrategyDesignMetaBar() {
  const wb = useStrategyDesignWorkbenchContext();
  const strategyLabel = resolveStrategyShortLabel({
    displayName: wb.strategyDisplayName,
    key: wb.strategyKey,
    name: wb.strategyName,
  });

  const goalLines = useMemo(
    () => formatGoalSummaryLines(wb.draftSettings?.goal || wb.initialSettings?.goal),
    [wb.draftSettings, wb.initialSettings],
  );

  const stepIntro = useMemo(() => {
    const intro = STRATEGY_DESIGN_STEP_INTRO[wb.activeStep];
    if (!intro) return { title: '制定策略', summary: '' };
    return intro;
  }, [wb.activeStep]);

  const capsuleTone = (wb.envInvalid || !wb.isAppliedSettings) ? 'changed' : 'clean';

  return (
    <section className="ntq-design-meta">
      <div className="ntq-design-meta__page-title">
        <h2 className="ntq-design-meta__page-heading">
          <span className="ntq-design-meta__page-heading-label">
            {stepIntro.title}
          </span>
          {stepIntro.summary ? (
            <>
              <span className="ntq-design-meta__page-heading-sep">：</span>
              <span className="ntq-design-meta__page-heading-summary">
                {stepIntro.summary}
              </span>
            </>
          ) : null}
        </h2>
        <div className="ntq-design-meta__page-title-stepper" data-ntq-help="strategy-steps">
          <StrategyDesignStepper />
        </div>
      </div>

      <div className="ntq-design-meta__body" data-ntq-help="strategy-intro">
        <div className="ntq-design-meta__info">
          <div className="ntq-design-meta__title-row">
            <Heading level="h3" gap="none" className="ntq-design-meta__strategy-name">
              {strategyLabel}
            </Heading>
            {wb.hasPersistedSnapshot ? (
              <div className="ntq-design-meta__version-capsule-wrap" data-ntq-help="strategy-version">
                <div
                  className={[
                    'ntq-design-meta__version-capsule',
                    `ntq-design-meta__version-capsule--${capsuleTone}`,
                  ].join(' ')}
                >
                  <span className="ntq-design-meta__version-capsule-part ntq-design-meta__version-capsule-part--version">
                    {wb.currentVersionDisplay}
                  </span>
                  <span className="ntq-design-meta__version-capsule-sep" aria-hidden />
                  <span className="ntq-design-meta__version-capsule-part ntq-design-meta__version-capsule-part--status">
                    {wb.capsuleStatus}
                  </span>
                </div>
              </div>
            ) : null}
          </div>

          <div
            className="ntq-design-meta__admin"
            data-ntq-help="strategy-actions"
          >
            <Button
              component={RouterLink}
              to={getStrategyListPath()}
              variant="glass"
              icon="arrowBack"
              iconSize="sm"
              className="ntq-design-meta__admin-action"
            >
              选择其他策略
            </Button>
            {wb.strategyName ? (
              <>
                <span className="ntq-design-meta__admin-sep" aria-hidden>|</span>
                <Button
                  variant="glass"
                  icon="folderOpen"
                  iconSize="sm"
                  onClick={wb.handleRevealStrategyFolder}
                  className="ntq-design-meta__admin-action"
                  tooltip="在文件管理器中打开策略目录"
                  data-ntq-help="strategy-open"
                >
                  打开文件夹
                </Button>
              </>
            ) : null}
            {wb.hasPersistedSnapshot ? (
              <>
                <span className="ntq-design-meta__admin-sep" aria-hidden>|</span>
                <Button
                  variant="glass"
                  icon="history"
                  iconSize="sm"
                  disabled={wb.disableMetaActions}
                  onClick={wb.openMoreVersionsDialog}
                  className="ntq-design-meta__admin-action"
                  data-ntq-help="strategy-history"
                >
                  恢复到历史版本
                </Button>
              </>
            ) : null}
            {wb.strategyName ? (
              <>
                <span className="ntq-design-meta__admin-sep" aria-hidden>|</span>
                <Button
                  variant="glass"
                  icon="download"
                  iconSize="sm"
                  disabled={wb.packageExporting}
                  onClick={wb.handleExportStrategyPackage}
                  className="ntq-design-meta__admin-action"
                  data-ntq-help="strategy-export"
                >
                  {wb.packageExporting ? '导出中…' : '导出策略'}
                </Button>
              </>
            ) : null}
          </div>

          <MetaFlash status="error">{wb.settingsError}</MetaFlash>
          <MetaFlash status="warning">{wb.marketProfileOptionsError}</MetaFlash>
          <MetaFlash status="error">{wb.saveError}</MetaFlash>
          <MetaFlash status="success">{wb.restoreOk}</MetaFlash>
          <MetaFlash status="error">{wb.packageExportError}</MetaFlash>
          <MetaFlash status="error">{wb.folderRevealError}</MetaFlash>
        </div>

        <div className="ntq-design-meta__description-col">
          <StrategyMetaDetailText
            entryConditions={wb.strategyEntryConditions}
            goalLines={goalLines}
            empty="暂无"
            className="ntq-design-meta__description"
          />
        </div>
      </div>
    </section>
  );
}

export default StrategyDesignMetaBar;
