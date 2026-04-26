import React from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Stack,
  Typography,
} from '@mui/material';
import Editor from '../../components/editor/editor';
import PriceSimulatorSettingsEditor from './components/priceSimulatorSettingsEditor';
import CapitalSimulatorSettingsEditor from './components/capitalSimulatorSettingsEditor';
import strategyCoreSchema from './editorSchemas/strategyCore';
import strategyEnumeratorSchema from './editorSchemas/strategyEnumerator';
import {
  applyGoalActions,
  normalizeGoalSettings,
} from './editorSchemas/strategyGoal';
import strategyGoalSchema from './editorSchemas/strategyGoal';
import strategyFeesSchema from './editorSchemas/strategyFees';
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
  coreEditor,
  onGoalChange,
  onSamplingChange,
  onFeesChange,
  onEnumeratorChange,
  onPriceSimulatorChange,
  onCapitalSimulatorChange,
}) {
  const shouldShowCore = hasNonEmptyCore(settings?.core);

  return (
    <SectionAccordion title="策略参数设置">
      <Stack spacing={1}>
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
          <PriceSimulatorSettingsEditor
            value={settings?.price_simulator}
            globalFees={settings?.fees}
            onChange={onPriceSimulatorChange}
          />
        </SectionAccordion>
        <SectionAccordion title="资金模拟参数">
          <CapitalSimulatorSettingsEditor
            value={settings?.capital_simulator}
            globalFees={settings?.fees}
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
