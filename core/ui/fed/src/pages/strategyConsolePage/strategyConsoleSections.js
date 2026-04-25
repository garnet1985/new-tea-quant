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
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';

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

export function MetaInfoSection({ meta }) {
  return (
    <SectionAccordion title="Meta 信息" defaultExpanded>
      <Stack spacing={1.5}>
        <Box>
          <Typography variant="caption" color="text.secondary">
            策略名
          </Typography>
          <Stack direction="row" alignItems="center" spacing={1} sx={{ mt: 0.5 }}>
            <Typography variant="body1" fontWeight={600}>
              {meta?.name || '--'}
            </Typography>
            <Tooltip title={meta?.description || ''} arrow>
              <InfoOutlinedIcon fontSize="small" color="action" />
            </Tooltip>
          </Stack>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            启用状态
          </Typography>
          <Box sx={{ mt: 0.5 }}>
            <Chip
              size="small"
              color={meta?.is_enabled ? 'success' : 'default'}
              label={meta?.is_enabled ? '已启用' : '已禁用'}
            />
          </Box>
        </Box>
      </Stack>
    </SectionAccordion>
  );
}

export function StrategySettingsSection({ settings }) {
  return (
    <SectionAccordion title="策略设置" defaultExpanded>
      <Stack spacing={1}>
        <SectionAccordion title="策略核心设施" defaultExpanded>
          <SettingsFields data={settings?.core} />
        </SectionAccordion>
        <SectionAccordion title="策略目标设置" defaultExpanded>
          <SettingsFields data={settings?.goal} />
        </SectionAccordion>
        <SectionAccordion title="枚举设置">
          <SettingsFields data={settings?.enumerator} />
        </SectionAccordion>
        <SectionAccordion title="价格回测">
          <SettingsFields data={settings?.price_simulator} />
        </SectionAccordion>
        <SectionAccordion title="资金模拟">
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
