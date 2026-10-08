import React, { useCallback, useMemo, useState } from 'react';
import NtqIcon from 'views/ntqIcon';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Stack,
  Typography,
} from '@mui/material';
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
import SettingsAccordionTitle from 'views/settingsAccordionTitle';
import {
  STRATEGY_DESIGN_SETTINGS_GLOBAL_TITLE,
  STRATEGY_DESIGN_SETTINGS_GLOBAL_TOOLTIP,
  STRATEGY_DESIGN_SETTINGS_STEP_TITLE,
} from '../constants/strategyDesignSettingsLayout';
import StrategyDesignPeerStrategies from '../peerStrategies';

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
    <Box className="ntq-design-settings-core-wrap">
      <Box className="ntq-design-settings-core-hint" aria-hidden={!showHint}>
        {showHint ? (
          <Typography variant="caption" color="text.secondary" component="p">
            修改核心参数后请回到枚举步重新运行。
          </Typography>
        ) : null}
      </Box>
      <Editor
        schema={strategyCoreSchema}
        value={settings}
        onChange={() => {}}
        context={coreEditorContext}
      />
    </Box>
  );
}

function SectionAccordion({
  title,
  tooltip = '',
  defaultExpanded = false,
  nested = true,
  children,
  context = {},
  helpTarget = '',
}) {
  const summaryTitle = (
    <SettingsAccordionTitle title={title} tooltip={tooltip} context={context} />
  );

  return (
    <Accordion
      className={nested ? 'ntq-settings-sub-accordion' : undefined}
      defaultExpanded={defaultExpanded}
      disableGutters
      TransitionProps={{ timeout: 0, unmountOnExit: false }}
      data-ntq-help={helpTarget || undefined}
    >
      <AccordionSummary expandIcon={<NtqIcon name="expandMore" size={24} />}>
        {summaryTitle}
      </AccordionSummary>
      <AccordionDetails>{children}</AccordionDetails>
    </Accordion>
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
          <SectionAccordion title="目标设置">
            <GoalSettingsEditor
              goal={settings?.goal}
              onGoalChange={onGoalChange}
              context={editorContext}
            />
          </SectionAccordion>
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
            <SectionAccordion title="价格回测参数">
              <SettingsSchemaEditor
                schema={strategyPriceSimulatorSchema}
                value={settings?.price_simulator}
                onChange={onPriceSimulatorChange}
                context={editorContext}
              />
            </SectionAccordion>
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
          <SectionAccordion title="投资模拟参数">
            <SettingsSchemaEditor
              schema={portfolioSchema}
              value={settings?.portfolio}
              onChange={onPortfolioChange}
              context={editorContext}
            />
          </SectionAccordion>
          <SectionAccordion title="交易费用">
            <SettingsSchemaEditor
              schema={strategyFeesSchema}
              value={settings?.fees}
              onChange={onFeesChange}
              context={editorContext}
            />
          </SectionAccordion>
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

  const globalSettingsBody = (
    <Stack spacing={1}>
      <SectionAccordion title="市场规则">
        <SettingsSchemaEditor
          schema={marketProfileSchema}
          value={settings}
          onChange={onSettingsChange}
          context={editorContext}
        />
      </SectionAccordion>
      <SectionAccordion title="数据设置">
        <SettingsSchemaEditor
          schema={strategyDataSchema}
          value={settings}
          onChange={onSettingsChange}
          context={editorContext}
        />
      </SectionAccordion>
      <SectionAccordion title="采样配置">
        <SamplingSettingsEditor
          sampling={settings?.sampling}
          onSamplingChange={onSamplingChange}
          schema={samplingSchema}
          context={editorContext}
        />
      </SectionAccordion>
      <SectionAccordion title="回测设置">
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
      </SectionAccordion>
    </Stack>
  );

  return (
    <Stack spacing={0} className="ntq-design-settings-panel">
      <SectionAccordion
        title={STRATEGY_DESIGN_SETTINGS_STEP_TITLE}
        defaultExpanded
        nested={false}
        helpTarget="design-settings-specific"
      >
        <Stack spacing={1}>{stepSettingsBody}</Stack>
      </SectionAccordion>
      <SectionAccordion
        title={STRATEGY_DESIGN_SETTINGS_GLOBAL_TITLE}
        tooltip={STRATEGY_DESIGN_SETTINGS_GLOBAL_TOOLTIP}
        defaultExpanded
        nested={false}
        context={editorContext}
        helpTarget="design-settings-global"
      >
        {globalSettingsBody}
      </SectionAccordion>
      <StrategyDesignPeerStrategies />
    </Stack>
  );
}

export default StrategyDesignSettingsPanel;
