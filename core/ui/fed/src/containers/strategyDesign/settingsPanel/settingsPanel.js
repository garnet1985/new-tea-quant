import React, { useCallback, useMemo, useState } from 'react';
import { Accordion } from 'ui';
import Editor from 'containers/editor';
import {
  GoalSettingsEditor,
  SamplingSettingsEditor,
  SettingsSchemaEditor,
  SimulationSettingsEditor,
  buildStrategyMetaSchema,
  buildStrategyPortfolioSchema,
  buildStrategySamplingSchema,
  buildStrategySimulationSchema,
  strategyCoreSchema,
  strategyDataSchema,
  strategyFeesSchema,
  strategyPriceSimulatorSchema,
} from 'containers/strategySettings';
import {
  STRATEGY_DESIGN_SETTINGS_GLOBAL_TITLE,
  STRATEGY_DESIGN_SETTINGS_GLOBAL_TOOLTIP,
  STRATEGY_DESIGN_SETTINGS_STEP_TITLE,
} from '../constants/strategyDesignSettingsLayout';
import StrategyDesignPeerStrategies from '../peerStrategies';
import './style.scss';

function buildMarketProfileOnlySchema(marketProfileOptions) {
  const meta = buildStrategyMetaSchema(marketProfileOptions);
  const marketProfileField = (meta.children || []).find((child) => child.name === 'market_profile');
  return {
    name: 'strategyMarketProfile',
    label: '',
    type: 'fieldGroup',
    children: marketProfileField
      ? [{ ...marketProfileField, label: '' }]
      : [],
  };
}

function CoreSettingsBlock({ showHint, coreEditorContext, settings }) {
  return (
    <div className="ntq-design-settings-core-wrap">
      <div className="ntq-design-settings-core-hint" aria-hidden={!showHint}>
        {showHint ? (
          <p className="ntq-muted">修改核心参数后请回到机会盘点步重新运行。</p>
        ) : null}
      </div>
      <Editor
        schema={strategyCoreSchema}
        value={settings}
        onChange={() => {}}
        context={coreEditorContext}
      />
    </div>
  );
}

const hasPriceSimulatorFields = Array.isArray(strategyPriceSimulatorSchema.children)
  && strategyPriceSimulatorSchema.children.length > 0;

function StrategyDesignSettingsPanel({
  activeStep,
  settings,
  onSettingsChange,
  coreEditor,
  onGoalChange,
  onSamplingChange,
  onFeesChange,
  onSimulationChange,
  onPriceSimulatorChange,
  onPortfolioChange,
  allocationModeOptions,
  samplingStrategyOptions,
  simulationTemplateOptions,
  simulationTemplateProfiles,
  skipInvestmentWhenOptions,
  marketProfileOptions,
}) {
  const [simulationEditorErrors, setSimulationEditorErrors] = useState({});

  const marketProfileSchema = useMemo(
    () => buildMarketProfileOnlySchema(marketProfileOptions),
    [marketProfileOptions],
  );
  const portfolioSchema = useMemo(
    () => buildStrategyPortfolioSchema(allocationModeOptions),
    [allocationModeOptions],
  );
  const samplingSchema = useMemo(
    () => buildStrategySamplingSchema(samplingStrategyOptions),
    [samplingStrategyOptions],
  );
  const simulationSchema = useMemo(
    () => buildStrategySimulationSchema(simulationTemplateOptions, skipInvestmentWhenOptions),
    [simulationTemplateOptions, skipInvestmentWhenOptions],
  );
  const editorContext = useMemo(() => ({ defaultTooltipShine: true }), []);
  const coreEditorContext = useMemo(
    () => ({ ...editorContext, coreEditor }),
    [editorContext, coreEditor],
  );

  const validateSimulationDates = useCallback((nextValue) => {
    const start = nextValue?.start_date || '';
    const end = nextValue?.end_date || '';
    const errors = {};
    if (start && end && end < start) {
      errors.end_date = '结束日期不能早于开始日期';
    }
    return errors;
  }, []);

  const showCoreHint = activeStep === 'price' || activeStep === 'portfolio';

  const stepSettingsBody = useMemo(() => {
    if (activeStep === 'enum') {
      return (
        <>
          <Accordion title="目标设置" variant="nested">
            <GoalSettingsEditor
              goal={settings?.goal}
              onGoalChange={onGoalChange}
              context={editorContext}
            />
          </Accordion>
          <Editor
            schema={strategyCoreSchema}
            value={settings}
            onChange={() => {}}
            context={coreEditorContext}
          />
        </>
      );
    }

    if (activeStep === 'price') {
      return (
        <>
          {hasPriceSimulatorFields ? (
            <Accordion title="价格回测参数" variant="nested">
              <SettingsSchemaEditor
                schema={strategyPriceSimulatorSchema}
                value={settings?.price_simulator}
                onChange={onPriceSimulatorChange}
                context={editorContext}
              />
            </Accordion>
          ) : null}
          <CoreSettingsBlock
            showHint={showCoreHint}
            coreEditorContext={coreEditorContext}
            settings={settings}
          />
        </>
      );
    }

    if (activeStep === 'portfolio') {
      return (
        <>
          <Accordion title="投资模拟参数" variant="nested">
            <SettingsSchemaEditor
              schema={portfolioSchema}
              value={settings?.portfolio}
              onChange={onPortfolioChange}
              context={editorContext}
            />
          </Accordion>
          <Accordion title="交易费用" variant="nested">
            <SettingsSchemaEditor
              schema={strategyFeesSchema}
              value={settings?.fees}
              onChange={onFeesChange}
              context={editorContext}
            />
          </Accordion>
          <CoreSettingsBlock
            showHint={showCoreHint}
            coreEditorContext={coreEditorContext}
            settings={settings}
          />
        </>
      );
    }

    return null;
  }, [
    activeStep,
    portfolioSchema,
    coreEditorContext,
    editorContext,
    onPortfolioChange,
    onFeesChange,
    onGoalChange,
    onPriceSimulatorChange,
    settings,
    showCoreHint,
  ]);

  return (
    <div className="ntq-design-settings-panel">
      <Accordion
        title={STRATEGY_DESIGN_SETTINGS_STEP_TITLE}
        defaultExpanded
        data-ntq-help="design-settings-specific"
      >
        <div className="ntq-design-settings-panel__stack">
          {stepSettingsBody}
        </div>
      </Accordion>
      <Accordion
        title={STRATEGY_DESIGN_SETTINGS_GLOBAL_TITLE}
        tooltip={STRATEGY_DESIGN_SETTINGS_GLOBAL_TOOLTIP}
        shine={Boolean(editorContext.defaultTooltipShine)}
        defaultExpanded
        data-ntq-help="design-settings-global"
      >
        <div className="ntq-design-settings-panel__stack">
          <Accordion title="市场规则" variant="nested">
            <SettingsSchemaEditor
              schema={marketProfileSchema}
              value={settings}
              onChange={onSettingsChange}
              context={editorContext}
            />
          </Accordion>
          <Accordion title="数据设置" variant="nested">
            <SettingsSchemaEditor
              schema={strategyDataSchema}
              value={settings}
              onChange={onSettingsChange}
              context={editorContext}
            />
          </Accordion>
          <Accordion title="采样配置" variant="nested">
            <SamplingSettingsEditor
              sampling={settings?.sampling}
              onSamplingChange={onSamplingChange}
              schema={samplingSchema}
              context={editorContext}
            />
          </Accordion>
          <Accordion title="回测设置" variant="nested">
            <SimulationSettingsEditor
              simulation={settings?.simulation}
              onSimulationChange={onSimulationChange}
              schema={simulationSchema}
              simulationTemplateProfiles={simulationTemplateProfiles}
              errors={simulationEditorErrors}
              onValidate={validateSimulationDates}
              onValidationChange={setSimulationEditorErrors}
              context={editorContext}
            />
          </Accordion>
        </div>
      </Accordion>
      <StrategyDesignPeerStrategies />
    </div>
  );
}

export default StrategyDesignSettingsPanel;
