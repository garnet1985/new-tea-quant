import React, { useCallback } from 'react';
import { Alert, Box, Grid, Stack } from '@mui/material';
import StrategyDesignExecutionPanel from './components/strategyDesignExecutionPanel';
import StrategyDesignReportPanel from './components/strategyDesignReportPanel';
import InlineLoadingState from 'components/inlineLoadingState/inlineLoadingState';
import StrategySettingsContainer from '../strategyWorkbenchPage/panels/strategySettingsPanel/containers/strategySettingsContainer';
import StrategyDesignDraftSync from './components/strategyDesignDraftSync';
import StrategyDesignDraftChangeBridge from './components/strategyDesignDraftChangeBridge';
import StrategyDesignSettingsPanel from './components/strategyDesignSettingsPanel';
import { useStrategyDesignSettingsOptions } from './hooks/useStrategyDesignSettingsOptions';
import { useStrategyDesignWorkbenchContext } from './strategyDesignWorkbenchContext';
import './strategyDesignStepPage.scss';

function StrategyDesignStepPage() {
  const wb = useStrategyDesignWorkbenchContext();
  const options = useStrategyDesignSettingsOptions();

  const handleDraftSync = useCallback((nextDraft) => {
    wb.setDraftSettings(nextDraft);
  }, [wb]);

  if (wb.isLoadingSettings) {
    return (
      <Box className="ntq-design-step-page">
        <InlineLoadingState compact row message="正在加载策略设置…" />
      </Box>
    );
  }

  return (
    <Box className="ntq-design-step-page">
      {wb.settingsError ? (
        <Alert severity="warning" sx={{ mb: 1.5 }}>{wb.settingsError}</Alert>
      ) : null}
      {options.optionsError ? (
        <Alert severity="warning" sx={{ mb: 1.5 }}>{options.optionsError}</Alert>
      ) : null}
      <StrategySettingsContainer initialSettings={wb.initialSettings}>
        {({
          draftSettings,
          setDraftSettings,
          coreEditor,
          onGoalChange,
          onSamplingChange,
          onFeesChange,
          onSimulationChange,
          onPriceSimulatorChange,
          onPortfolioChange,
        }) => (
          <>
            <StrategyDesignDraftSync
              draftSettings={draftSettings}
              onDraftSettingsChange={handleDraftSync}
            />
            <StrategyDesignDraftChangeBridge
              draftSettings={draftSettings}
              strategyName={wb.strategyName}
              isLoadingSettings={wb.isLoadingSettings}
              onReset={wb.handleDraftDrivenReset}
              suppressDraftDrivenPanelResetRef={wb.suppressDraftDrivenPanelResetRef}
            />
            <Grid container spacing={2} className="ntq-design-step-page__grid">
              <Grid item xs={12} md={3}>
                <Box className="ntq-design-step-page__settings">
                  <StrategyDesignSettingsPanel
                    activeStep={wb.activeStep}
                    settings={draftSettings}
                    onSettingsChange={setDraftSettings}
                    coreEditor={coreEditor}
                    onGoalChange={onGoalChange}
                    onSamplingChange={onSamplingChange}
                    onFeesChange={onFeesChange}
                    onSimulationChange={onSimulationChange}
                    onPriceSimulatorChange={onPriceSimulatorChange}
                    onPortfolioChange={onPortfolioChange}
                    allocationModeOptions={options.allocationModeOptions}
                    samplingStrategyOptions={options.samplingStrategyOptions}
                    simulationTemplateOptions={options.simulationTemplateOptions}
                    simulationTemplateProfiles={options.simulationTemplateProfiles}
                    skipInvestmentWhenOptions={options.skipInvestmentWhenOptions}
                    marketProfileOptions={options.marketProfileOptions}
                  />
                </Box>
              </Grid>
              <Grid item xs={12} md={9}>
                <Stack spacing={1.5} className="ntq-design-step-page__right">
                  <StrategyDesignExecutionPanel />
                  <StrategyDesignReportPanel />
                </Stack>
              </Grid>
            </Grid>
          </>
        )}
      </StrategySettingsContainer>
    </Box>
  );
}

export default StrategyDesignStepPage;
