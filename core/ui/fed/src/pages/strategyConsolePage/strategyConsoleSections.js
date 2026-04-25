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

function formatPrimitive(value) {
  if (typeof value === 'boolean') return value ? 'true' : 'false';
  if (value === null || value === undefined) return '';
  return String(value);
}

function SettingsFields({ data, level = 0 }) {
  if (!isPlainObject(data)) {
    return (
      <Typography variant="body2" color="text.secondary">
        无可展示字段
      </Typography>
    );
  }

  return (
    <Stack spacing={1.25}>
      {Object.entries(data || {}).map(([key, value]) => (
        isPlainObject(value) ? (
          <Box
            key={key}
            sx={{
              border: 1,
              borderColor: 'divider',
              borderRadius: 1,
              p: 1.25,
              backgroundColor: level > 0 ? 'action.hover' : 'transparent',
            }}
          >
            <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
              {key}
            </Typography>
            <SettingsFields data={value} level={level + 1} />
          </Box>
        ) : (
          <TextField
            key={key}
            size="small"
            label={key}
            value={Array.isArray(value) ? JSON.stringify(value) : formatPrimitive(value)}
            fullWidth
            variant="outlined"
            InputProps={{ readOnly: true }}
          />
        )
      ))}
    </Stack>
  );
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

export function StrategySettingsSection({ settings, coreEditor, onGoalChange }) {
  const shouldShowCore = hasNonEmptyCore(settings?.core);

  return (
    <SectionAccordion title="策略参数设置" defaultExpanded>
      <Stack spacing={1}>
        {shouldShowCore ? (
          <SectionAccordion title="策略核心设置" defaultExpanded>
            <CoreDictEditorView {...coreEditor} />
          </SectionAccordion>
        ) : null}
        <SectionAccordion title="策略目标设置" defaultExpanded>
          <GoalSettingsEditor value={settings?.goal} onChange={onGoalChange} />
        </SectionAccordion>
        <SectionAccordion title="机会枚举参数">
          <SettingsFields data={settings?.enumerator} />
        </SectionAccordion>
        <SectionAccordion title="价格回测参数">
          <SettingsFields data={settings?.price_simulator} />
        </SectionAccordion>
        <SectionAccordion title="资金模拟参数">
          <SettingsFields data={settings?.capital_simulator} />
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
