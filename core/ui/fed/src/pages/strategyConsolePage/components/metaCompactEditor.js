import React from 'react';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Chip,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';

function MetaCompactEditor({
  sectionTitle,
  value,
  onChange,
  simulationRange,
  onSimulationRangeChange,
  minRequiredRecords,
  onMinRequiredRecordsChange,
  defaultExpanded = false,
}) {
  const meta = value || {};
  const enabled = Boolean(meta.is_enabled);
  const dateFrom = simulationRange?.from || '';
  const dateTo = simulationRange?.to || '';

  return (
    <Accordion defaultExpanded={defaultExpanded} disableGutters>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography fontWeight={600}>{sectionTitle}</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1.25}>
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: 1,
            }}
          >
            <Typography variant="body2" color="text.secondary">
              是否启用策略
            </Typography>
            <Stack direction="row" alignItems="center" spacing={0.5}>
              <Switch
                size="small"
                checked={enabled}
                onChange={(e) => {
                  if (!onChange) return;
                  onChange({ ...meta, is_enabled: e.target.checked });
                }}
              />
              <Chip
                size="small"
                color={enabled ? 'success' : 'default'}
                label={enabled ? '已启用' : '已禁用'}
              />
            </Stack>
          </Box>
          <Typography variant="body2" color="text.secondary">
            模拟时间段
          </Typography>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
            <TextField
              size="small"
              type="date"
              label="From"
              value={dateFrom}
              onChange={(e) => {
                if (!onSimulationRangeChange) return;
                onSimulationRangeChange({ from: e.target.value, to: dateTo });
              }}
              fullWidth
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              size="small"
              type="date"
              label="To"
              value={dateTo}
              onChange={(e) => {
                if (!onSimulationRangeChange) return;
                onSimulationRangeChange({ from: dateFrom, to: e.target.value });
              }}
              fullWidth
              InputLabelProps={{ shrink: true }}
            />
          </Stack>
          <TextField
            size="small"
            type="number"
            label="模拟需要的最少K线数量"
            value={minRequiredRecords ?? ''}
            onChange={(e) => {
              if (!onMinRequiredRecordsChange) return;
              const raw = e.target.value;
              if (raw === '') {
                onMinRequiredRecordsChange('');
                return;
              }
              const n = Number(raw);
              onMinRequiredRecordsChange(Number.isNaN(n) ? '' : n);
            }}
            fullWidth
            helperText="至少满足该历史记录条数才执行策略（默认 100）"
          />
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}

export default MetaCompactEditor;
