import React, { useCallback, useMemo, useState } from 'react';
import NtqIcon from 'components/ntqIcon/ntqIcon';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Stack,
  Typography,
} from '@mui/material';
import Editor from 'components/editor/editor';
import strategyCoreSchema from './editorSchemas/strategyCore';
import strategyDataSchema from './editorSchemas/strategyData';
import { buildStrategyMetaSchema } from './editorSchemas/strategyMeta';
import strategyFeesSchema from './editorSchemas/strategyFees';
import {
  STRATEGY_SETTINGS_ROOT_TITLE,
  STRATEGY_SETTINGS_ROOT_TOOLTIP,
} from './settingsSectionMeta';
import SettingsAccordionTitle from 'components/settingsAccordionTitle/settingsAccordionTitle';
import strategyPriceSimulatorSchema from './editorSchemas/strategyPriceSimulator';
import { buildStrategyPortfolioSchema } from './editorSchemas/strategyPortfolio';
import { buildStrategySamplingSchema } from './editorSchemas/strategySampling';
import { buildStrategySimulationSchema } from './editorSchemas/strategySimulation';
import {
  GoalSettingsEditor,
  SamplingSettingsEditor,
  SettingsSchemaEditor,
  SimulationSettingsEditor,
} from './settingsEditorSections';

function SectionAccordion({
  title,
  tooltip = '',
  defaultExpanded = false,
  nested = true,
  children,
  context = {},
}) {
  const summaryTitle = tooltip ? (
    <SettingsAccordionTitle title={title} tooltip={tooltip} context={context} />
  ) : (
    <Typography component="span" fontWeight={600}>
      {title}
    </Typography>
  );

  return (
    <Accordion
      className={nested ? 'ntq-settings-sub-accordion' : undefined}
      defaultExpanded={defaultExpanded}
      disableGutters
      TransitionProps={{ timeout: 0, unmountOnExit: false }}
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

export function StrategySettingsPanel({
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
  const metaSchema = useMemo(
    () => buildStrategyMetaSchema(marketProfileOptions),
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
  const workbenchEditorContext = useMemo(() => ({ defaultTooltipShine: true }), []);
  const coreEditorContext = useMemo(
    () => ({ ...workbenchEditorContext, coreEditor }),
    [workbenchEditorContext, coreEditor],
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

  return (
    <SectionAccordion
      title={STRATEGY_SETTINGS_ROOT_TITLE}
      tooltip={STRATEGY_SETTINGS_ROOT_TOOLTIP}
      context={workbenchEditorContext}
      defaultExpanded
      nested={false}
    >
      <Stack spacing={1}>
        <SettingsSchemaEditor
          schema={metaSchema}
          value={settings}
          onChange={onSettingsChange}
          context={workbenchEditorContext}
        />
        <SectionAccordion title="数据设置">
          <SettingsSchemaEditor
            schema={strategyDataSchema}
            value={settings}
            onChange={onSettingsChange}
            context={workbenchEditorContext}
          />
        </SectionAccordion>
        <Editor
          schema={strategyCoreSchema}
          value={settings}
          onChange={() => {}}
          context={coreEditorContext}
        />
        <SectionAccordion title="目标设置">
          <GoalSettingsEditor
            goal={settings?.goal}
            onGoalChange={onGoalChange}
            context={workbenchEditorContext}
          />
        </SectionAccordion>
        <SectionAccordion title="交易费用">
          <SettingsSchemaEditor
            schema={strategyFeesSchema}
            value={settings?.fees}
            onChange={onFeesChange}
            context={workbenchEditorContext}
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
            context={workbenchEditorContext}
          />
        </SectionAccordion>
        <SectionAccordion title="采样配置">
          <SamplingSettingsEditor
            sampling={settings?.sampling}
            onSamplingChange={onSamplingChange}
            schema={samplingSchema}
            context={workbenchEditorContext}
          />
        </SectionAccordion>
        {hasPriceSimulatorFields ? (
          <SectionAccordion title="价格回测参数">
            <SettingsSchemaEditor
              schema={strategyPriceSimulatorSchema}
              value={settings?.price_simulator}
              onChange={onPriceSimulatorChange}
              context={workbenchEditorContext}
            />
          </SectionAccordion>
        ) : null}
        <SectionAccordion title="资金组合参数">
          <SettingsSchemaEditor
            schema={portfolioSchema}
            value={settings?.portfolio}
            onChange={onPortfolioChange}
            context={workbenchEditorContext}
          />
        </SectionAccordion>
      </Stack>
    </SectionAccordion>
  );
}

export function PlaceholderSection({
  title,
  text,
  defaultExpanded = false,
  children,
}) {
  return (
    <SectionAccordion title={title} defaultExpanded={defaultExpanded} nested={false}>
      {children || (
        <Typography variant="body2" color="text.secondary">
          {text || '敬请期待…'}
        </Typography>
      )}
    </SectionAccordion>
  );
}
