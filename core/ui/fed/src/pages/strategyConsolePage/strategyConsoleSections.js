import React from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Chip,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';
import CoreDictEditorView from './components/coreDictEditorView';
import GoalSettingsEditor from './components/goalSettingsEditor';
import SamplingSettingsEditor from './components/samplingSettingsEditor';
import FeesConfigEditor from './components/feesConfigEditor';
import EnumeratorSettingsEditor from './components/enumeratorSettingsEditor';
import PriceSimulatorSettingsEditor from './components/priceSimulatorSettingsEditor';
import CapitalSimulatorSettingsEditor from './components/capitalSimulatorSettingsEditor';

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

export function MetaInfoSection({ meta, model = [], onMetaChange }) {
  const fields = Array.isArray(model) && model.length > 0
    ? model
    : [
        { key: 'name', displayNameZh: '策略名', type: 'text', readonly: true },
        { key: 'description', displayNameZh: '描述', type: 'text', readonly: true },
        { key: 'is_enabled', displayNameZh: '启用状态', type: 'boolean', readonly: false },
      ];

  return (
    <SectionAccordion title="Meta 信息" defaultExpanded>
      <Stack spacing={1.5}>
        {fields.map((field) => {
          const value = meta?.[field.key];
          if (field.key === 'name') {
            return (
              <Box key={field.key}>
                <Typography variant="caption" color="text.secondary">
                  {field.displayNameZh}
                </Typography>
                <Stack direction="row" alignItems="center" spacing={1} sx={{ mt: 0.5 }}>
                  <Typography variant="body1" fontWeight={600}>
                    {value || '--'}
                  </Typography>
                  <Tooltip title={meta?.description || ''} arrow>
                    <InfoOutlinedIcon fontSize="small" color="action" />
                  </Tooltip>
                </Stack>
              </Box>
            );
          }

          if (field.type === 'boolean') {
            return (
              <Box key={field.key}>
                <Typography variant="caption" color="text.secondary">
                  {field.displayNameZh}
                </Typography>
                <Stack direction="row" alignItems="center" spacing={1} sx={{ mt: 0.5 }}>
                  <Switch
                    size="small"
                    checked={Boolean(value)}
                    disabled={field.readonly}
                    onChange={(e) => {
                      if (!onMetaChange) return;
                      onMetaChange({ ...meta, [field.key]: e.target.checked });
                    }}
                  />
                  <Chip
                    size="small"
                    color={Boolean(value) ? 'success' : 'default'}
                    label={Boolean(value) ? '已启用' : '已禁用'}
                  />
                </Stack>
              </Box>
            );
          }

          return (
            <TextField
              key={field.key}
              size="small"
              label={field.displayNameZh}
              value={value ?? ''}
              fullWidth
              InputProps={{ readOnly: true }}
            />
          );
        })}
      </Stack>
    </SectionAccordion>
  );
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
          <SectionAccordion title="策略核心设置">
            <CoreDictEditorView {...coreEditor} />
          </SectionAccordion>
        ) : null}
        <SectionAccordion title="策略目标设置">
          <GoalSettingsEditor value={settings?.goal} onChange={onGoalChange} />
        </SectionAccordion>
        <SectionAccordion title="全局费用设置">
          <FeesConfigEditor value={settings?.fees} onChange={onFeesChange} />
        </SectionAccordion>
        <SectionAccordion title="机会枚举参数">
          <EnumeratorSettingsEditor value={settings?.enumerator} onChange={onEnumeratorChange} />
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
          <SamplingSettingsEditor value={settings?.sampling} onChange={onSamplingChange} />
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
