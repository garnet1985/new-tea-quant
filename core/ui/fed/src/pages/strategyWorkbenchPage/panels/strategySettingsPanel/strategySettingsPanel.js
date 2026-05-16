import React, { useMemo, useState } from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Stack,
  Typography,
} from '@mui/material';
import Editor from 'components/editor/editor';
import strategyCoreSchema from './editorSchemas/strategyCore';
import strategyMetaSchema from './editorSchemas/strategyMeta';
import {
  applyGoalActions,
  normalizeGoalSettings,
} from './editorSchemas/strategyGoal';
import strategyGoalSchema from './editorSchemas/strategyGoal';
import strategyFeesSchema from './editorSchemas/strategyFees';
import strategyPriceSimulatorSchema from './editorSchemas/strategyPriceSimulator';
import { buildStrategyCapitalSimulatorSchema } from './editorSchemas/strategyCapitalSimulator';
import {
  buildStrategySamplingSchema,
  cleanupSamplingByStrategy,
  normalizeSamplingSettings,
} from './editorSchemas/strategySampling';
import {
  buildStrategySimulationSchema,
  cleanupSimulationByTemplate,
  normalizeSimulationSettings,
} from './editorSchemas/strategySimulation';

function SectionAccordion({ title, defaultExpanded = false, children }) {
  return (
    <Accordion defaultExpanded={defaultExpanded} disableGutters>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography fontWeight={600}>{title}</Typography>
      </AccordionSummary>
      <AccordionDetails>{children}</AccordionDetails>
    </Accordion>
  );
}

function isPlainObject(value) {
  return Object.prototype.toString.call(value) === '[object Object]';
}

function hasNonEmptyCore(value) {
  return isPlainObject(value) && Object.keys(value).length > 0;
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
  onCapitalSimulatorChange,
  allocationModeOptions,
  samplingStrategyOptions,
  simulationTemplateOptions,
}) {
  const shouldShowCore = hasNonEmptyCore(settings?.core);
  const [samplingEditorErrors, setSamplingEditorErrors] = useState({});
  const capitalSimulatorSchema = useMemo(
    () => buildStrategyCapitalSimulatorSchema(allocationModeOptions),
    [allocationModeOptions],
  );
  const samplingSchema = useMemo(
    () => buildStrategySamplingSchema(samplingStrategyOptions),
    [samplingStrategyOptions],
  );
  const simulationSchema = useMemo(
    () => buildStrategySimulationSchema(simulationTemplateOptions),
    [simulationTemplateOptions],
  );

  return (
    <SectionAccordion title="策略参数设置" defaultExpanded>
      <Stack spacing={1}>
        <Editor
          schema={strategyMetaSchema}
          value={settings}
          onChange={onSettingsChange}
        />
        {shouldShowCore ? (
          <Editor
            schema={strategyCoreSchema}
            value={settings}
            onChange={() => {}}
            context={{ coreEditor }}
          />
        ) : null}
        <SectionAccordion title="策略目标设置">
          <Editor
            schema={strategyGoalSchema}
            value={normalizeGoalSettings(settings?.goal)}
            onChange={(nextValue) => {
              const nextGoal = applyGoalActions(nextValue || {});
              onGoalChange(nextGoal);
            }}
          />
        </SectionAccordion>
        <SectionAccordion title="全局费用设置">
          <Editor
            schema={strategyFeesSchema}
            value={settings?.fees}
            onChange={onFeesChange}
          />
        </SectionAccordion>
        <SectionAccordion title="回测执行假设">
          <Editor
            schema={simulationSchema}
            value={normalizeSimulationSettings(settings?.simulation)}
            onChange={(nextSimulation) => {
              onSimulationChange(cleanupSimulationByTemplate(nextSimulation));
            }}
          />
        </SectionAccordion>
        <SectionAccordion title="采样配置">
          <Editor
            schema={samplingSchema}
            value={normalizeSamplingSettings(settings?.sampling)}
            onChange={(nextSampling) => onSamplingChange(cleanupSamplingByStrategy(nextSampling))}
            errors={samplingEditorErrors}
            onValidate={(nextValue) => {
              const start = nextValue?.start_date || '';
              const end = nextValue?.end_date || '';
              const errors = {};
              if (start && end && end < start) {
                errors.end_date = '结束日期不能早于开始日期';
              }
              return errors;
            }}
            onValidationChange={setSamplingEditorErrors}
          />
        </SectionAccordion>
        {hasPriceSimulatorFields ? (
          <SectionAccordion title="价格回测参数">
            <Editor
              schema={strategyPriceSimulatorSchema}
              value={settings?.price_simulator}
              onChange={onPriceSimulatorChange}
            />
          </SectionAccordion>
        ) : null}
        <SectionAccordion title="资金模拟参数">
          <Editor
            schema={capitalSimulatorSchema}
            value={settings?.capital_simulator}
            onChange={onCapitalSimulatorChange}
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
    <SectionAccordion title={title} defaultExpanded={defaultExpanded}>
      {children || (
        <Typography variant="body2" color="text.secondary">
          {text || '敬请期待…'}
        </Typography>
      )}
    </SectionAccordion>
  );
}
