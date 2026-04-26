import React, { useState } from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Stack,
  Typography,
} from '@mui/material';
import Editor from '../../components/editor/editor';
import strategyCoreSchema from './editorSchemas/strategyCore';
import strategyMetaSchema from './editorSchemas/strategyMeta';
import strategyEnumeratorSchema from './editorSchemas/strategyEnumerator';
import {
  applyGoalActions,
  normalizeGoalSettings,
} from './editorSchemas/strategyGoal';
import strategyGoalSchema from './editorSchemas/strategyGoal';
import strategyFeesSchema from './editorSchemas/strategyFees';
import strategyPriceSimulatorSchema from './editorSchemas/strategyPriceSimulator';
import strategyCapitalSimulatorSchema from './editorSchemas/strategyCapitalSimulator';
import strategySamplingSchema, {
  cleanupSamplingByStrategy,
  normalizeSamplingSettings,
} from './editorSchemas/strategySampling';

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

export function StrategySettingsSection({
  settings,
  onSettingsChange,
  coreEditor,
  onGoalChange,
  onSamplingChange,
  onFeesChange,
  onEnumeratorChange,
  onPriceSimulatorChange,
  onCapitalSimulatorChange,
}) {
  const shouldShowCore = hasNonEmptyCore(settings?.core);
  const [metaEditorErrors, setMetaEditorErrors] = useState({});

  return (
    <SectionAccordion title="策略参数设置" defaultExpanded>
      <Stack spacing={1}>
        <Editor
          schema={strategyMetaSchema}
          value={settings}
          onChange={onSettingsChange}
          errors={metaEditorErrors}
          onValidate={(nextValue) => {
            const start = nextValue?.price_simulator?.start_date || '';
            const end = nextValue?.price_simulator?.end_date || '';
            const errors = {};
            if (start && end && end < start) {
              errors['price_simulator.end_date'] = '结束日期不能早于开始日期';
            }
            return errors;
          }}
          onValidationChange={setMetaEditorErrors}
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
        <SectionAccordion title="机会枚举参数">
          <Editor
            schema={strategyEnumeratorSchema}
            value={settings?.enumerator}
            onChange={onEnumeratorChange}
          />
        </SectionAccordion>
        <SectionAccordion title="价格回测参数">
          <Editor
            schema={strategyPriceSimulatorSchema}
            value={settings?.price_simulator}
            onChange={onPriceSimulatorChange}
          />
        </SectionAccordion>
        <SectionAccordion title="资金模拟参数">
          <Editor
            schema={strategyCapitalSimulatorSchema}
            value={settings?.capital_simulator}
            onChange={onCapitalSimulatorChange}
          />
        </SectionAccordion>
        <SectionAccordion title="采样配置">
          <Editor
            schema={strategySamplingSchema}
            value={normalizeSamplingSettings(settings?.sampling)}
            onChange={(nextSampling) => onSamplingChange(cleanupSamplingByStrategy(nextSampling))}
          />
        </SectionAccordion>
      </Stack>
    </SectionAccordion>
  );
}

export function PlaceholderSection({ title, text, defaultExpanded = false }) {
  return (
    <SectionAccordion title={title} defaultExpanded={defaultExpanded}>
      <Typography variant="body2" color="text.secondary">
        {text || 'Coming soon...'}
      </Typography>
    </SectionAccordion>
  );
}
