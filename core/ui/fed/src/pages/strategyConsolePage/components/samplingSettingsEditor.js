import React, { useMemo } from 'react';
import {
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';

const SAMPLING_STRATEGIES = [
  'uniform',
  'stratified',
  'random',
  'pool',
  'blacklist',
];

function toNumberOrEmpty(value) {
  if (value === '' || value === null || value === undefined) return '';
  const n = Number(value);
  return Number.isNaN(n) ? '' : n;
}

function parseStockIds(text) {
  return String(text || '')
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeSampling(rawSampling) {
  const strategy = SAMPLING_STRATEGIES.includes(rawSampling?.strategy)
    ? rawSampling.strategy
    : 'uniform';
  return {
    strategy,
    sampling_amount: toNumberOrEmpty(rawSampling?.sampling_amount ?? 10),
    stratifiedSeed: toNumberOrEmpty(rawSampling?.stratified?.seed),
    randomSeed: toNumberOrEmpty(rawSampling?.random?.seed),
    poolStockIds: Array.isArray(rawSampling?.pool?.stock_ids) ? rawSampling.pool.stock_ids : [],
    poolFile: rawSampling?.pool?.file || '',
    blacklistStockIds: Array.isArray(rawSampling?.blacklist?.stock_ids)
      ? rawSampling.blacklist.stock_ids
      : [],
    blacklistFile: rawSampling?.blacklist?.file || '',
  };
}

function buildSamplingPayload(sourceSampling, normalized) {
  const next = { ...(sourceSampling || {}) };
  next.strategy = normalized.strategy;
  next.sampling_amount = normalized.sampling_amount;

  delete next.uniform;
  delete next.stratified;
  delete next.random;
  delete next.pool;
  delete next.blacklist;

  if (normalized.strategy === 'uniform') {
    next.uniform = {};
  } else if (normalized.strategy === 'stratified') {
    next.stratified = {};
    if (normalized.stratifiedSeed !== '') {
      next.stratified.seed = normalized.stratifiedSeed;
    }
  } else if (normalized.strategy === 'random') {
    next.random = {};
    if (normalized.randomSeed !== '') {
      next.random.seed = normalized.randomSeed;
    }
  } else if (normalized.strategy === 'pool') {
    next.pool = {};
    if (normalized.poolStockIds.length > 0) {
      next.pool.stock_ids = normalized.poolStockIds;
    }
    if (normalized.poolFile) {
      next.pool.file = normalized.poolFile;
    }
  } else if (normalized.strategy === 'blacklist') {
    next.blacklist = {};
    if (normalized.blacklistStockIds.length > 0) {
      next.blacklist.stock_ids = normalized.blacklistStockIds;
    }
    if (normalized.blacklistFile) {
      next.blacklist.file = normalized.blacklistFile;
    }
  }

  return next;
}

function SamplingSettingsEditor({ value, onChange }) {
  const normalized = useMemo(() => normalizeSampling(value || {}), [value]);

  const emit = (patch) => {
    if (!onChange) return;
    const merged = { ...normalized, ...patch };
    onChange(buildSamplingPayload(value, merged));
  };

  return (
    <Stack spacing={1.25}>
      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Typography fontWeight={600} sx={{ mb: 1 }}>
          采样基础配置
        </Typography>
        <Stack spacing={1}>
          <div>
            <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
              采样策略
            </Typography>
            <Select
              size="small"
              fullWidth
              value={normalized.strategy}
              onChange={(e) => emit({ strategy: e.target.value })}
            >
              {SAMPLING_STRATEGIES.map((strategy) => (
                <MenuItem key={strategy} value={strategy}>
                  {strategy}
                </MenuItem>
              ))}
            </Select>
          </div>
          <TextField
            size="small"
            type="number"
            label="采样数量"
            value={normalized.sampling_amount}
            onChange={(e) => emit({ sampling_amount: toNumberOrEmpty(e.target.value) })}
            fullWidth
          />
        </Stack>
      </Paper>

      {normalized.strategy === 'stratified' ? (
        <Paper variant="outlined" sx={{ p: 1.25 }}>
          <TextField
            size="small"
            type="number"
            label="分层采样随机种子"
            value={normalized.stratifiedSeed}
            onChange={(e) => emit({ stratifiedSeed: toNumberOrEmpty(e.target.value) })}
            fullWidth
          />
        </Paper>
      ) : null}

      {normalized.strategy === 'random' ? (
        <Paper variant="outlined" sx={{ p: 1.25 }}>
          <TextField
            size="small"
            type="number"
            label="随机采样随机种子"
            value={normalized.randomSeed}
            onChange={(e) => emit({ randomSeed: toNumberOrEmpty(e.target.value) })}
            fullWidth
          />
        </Paper>
      ) : null}

      {normalized.strategy === 'pool' ? (
        <Paper variant="outlined" sx={{ p: 1.25 }}>
          <Stack spacing={1}>
            <TextField
              size="small"
              multiline
              minRows={4}
              label="股票池列表（每行一个，或逗号分隔）"
              value={normalized.poolStockIds.join('\n')}
              onChange={(e) => emit({ poolStockIds: parseStockIds(e.target.value) })}
              fullWidth
            />
            <TextField
              size="small"
              label="股票池文件路径（可选）"
              value={normalized.poolFile}
              onChange={(e) => emit({ poolFile: e.target.value })}
              fullWidth
            />
          </Stack>
        </Paper>
      ) : null}

      {normalized.strategy === 'blacklist' ? (
        <Paper variant="outlined" sx={{ p: 1.25 }}>
          <Stack spacing={1}>
            <TextField
              size="small"
              multiline
              minRows={4}
              label="黑名单列表（每行一个，或逗号分隔）"
              value={normalized.blacklistStockIds.join('\n')}
              onChange={(e) => emit({ blacklistStockIds: parseStockIds(e.target.value) })}
              fullWidth
            />
            <TextField
              size="small"
              label="黑名单文件路径（可选）"
              value={normalized.blacklistFile}
              onChange={(e) => emit({ blacklistFile: e.target.value })}
              fullWidth
            />
          </Stack>
        </Paper>
      ) : null}
    </Stack>
  );
}

export default SamplingSettingsEditor;
