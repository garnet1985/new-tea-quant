import React, { useMemo } from 'react';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import AddIcon from '@mui/icons-material/Add';
import {
  Box,
  Button,
  Divider,
  IconButton,
  MenuItem,
  Paper,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';

const ACTION_SET_PROTECT_LOSS = 'set_protect_loss';
const ACTION_SET_DYNAMIC_LOSS = 'set_dynamic_loss';

function toNumberOrEmpty(value) {
  if (value === '' || value === null || value === undefined) return '';
  const n = Number(value);
  return Number.isNaN(n) ? '' : n;
}

function normalizeStage(stage) {
  return {
    name: stage?.name || '',
    ratio: toNumberOrEmpty(stage?.ratio),
    close_invest: Boolean(stage?.close_invest),
    sell_ratio: toNumberOrEmpty(stage?.sell_ratio),
    actions: Array.isArray(stage?.actions) ? stage.actions : [],
  };
}

function normalizeGoal(goal) {
  return {
    expiration: {
      fixed_window_in_days: toNumberOrEmpty(goal?.expiration?.fixed_window_in_days ?? 30),
      is_trading_days: goal?.expiration?.is_trading_days !== false,
    },
    stop_loss: {
      stages: Array.isArray(goal?.stop_loss?.stages)
        ? goal.stop_loss.stages.map(normalizeStage)
        : [],
    },
    take_profit: {
      stages: Array.isArray(goal?.take_profit?.stages)
        ? goal.take_profit.stages.map(normalizeStage)
        : [],
    },
    protect_loss: goal?.protect_loss
      ? {
          ratio: toNumberOrEmpty(goal.protect_loss.ratio),
          close_invest: Boolean(goal.protect_loss.close_invest),
        }
      : undefined,
    dynamic_loss: goal?.dynamic_loss
      ? {
          ratio: toNumberOrEmpty(goal.dynamic_loss.ratio),
          close_invest: Boolean(goal.dynamic_loss.close_invest),
        }
      : undefined,
  };
}

function sanitizeGoalByActions(goal) {
  const stages = goal?.take_profit?.stages || [];
  const hasProtectLossAction = stages.some((stage) => stage.actions?.includes(ACTION_SET_PROTECT_LOSS));
  const hasDynamicLossAction = stages.some((stage) => stage.actions?.includes(ACTION_SET_DYNAMIC_LOSS));

  const next = { ...goal };
  if (!hasProtectLossAction) {
    delete next.protect_loss;
  } else if (!next.protect_loss) {
    next.protect_loss = { ratio: 0, close_invest: true };
  } else {
    next.protect_loss = {
      ...next.protect_loss,
      close_invest: true,
    };
  }

  if (!hasDynamicLossAction) {
    delete next.dynamic_loss;
  } else if (!next.dynamic_loss) {
    next.dynamic_loss = { ratio: -0.1, close_invest: true };
  }

  return next;
}

function StageEditor({ title, stages, onChange, enableActions = false }) {
  const updateStage = (idx, patch) => {
    const nextStages = [...stages];
    nextStages[idx] = { ...nextStages[idx], ...patch };
    onChange(nextStages);
  };

  const removeStage = (idx) => {
    const nextStages = stages.filter((_, index) => index !== idx);
    onChange(nextStages);
  };

  const addStage = () => {
    onChange([
      ...stages,
      {
        name: '',
        ratio: '',
        close_invest: false,
        sell_ratio: '',
        actions: [],
      },
    ]);
  };

  return (
    <Paper variant="outlined" sx={{ p: 1.25 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
        <Typography fontWeight={600}>{title}</Typography>
        <Button size="small" startIcon={<AddIcon />} onClick={addStage}>
          新增阶段
        </Button>
      </Stack>

      <Stack spacing={1}>
        {stages.map((stage, idx) => (
          <Box key={`${title}-${idx}`} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1 }}>
            <Stack direction="row" spacing={1} alignItems="flex-start">
              <Stack spacing={1} sx={{ flex: 1 }}>
                <TextField
                  size="small"
                  label="阶段名称"
                  value={stage.name}
                  onChange={(e) => updateStage(idx, { name: e.target.value })}
                  fullWidth
                />
                <TextField
                  size="small"
                  label="触发比例"
                  type="number"
                  value={stage.ratio}
                  onChange={(e) => updateStage(idx, { ratio: toNumberOrEmpty(e.target.value) })}
                  fullWidth
                />
                <Stack direction="row" spacing={1} alignItems="center">
                  <Switch
                    size="small"
                    checked={Boolean(stage.close_invest)}
                    onChange={(e) => updateStage(idx, { close_invest: e.target.checked })}
                  />
                  <Typography variant="body2">触发清仓</Typography>
                </Stack>
                {!stage.close_invest ? (
                  <TextField
                    size="small"
                    label="卖出比例（0~1）"
                    type="number"
                    value={stage.sell_ratio}
                    onChange={(e) => updateStage(idx, { sell_ratio: toNumberOrEmpty(e.target.value) })}
                    fullWidth
                  />
                ) : null}
                {enableActions ? (
                  <Box>
                    <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                      触发动作
                    </Typography>
                    <Select
                      size="small"
                      multiple
                      value={stage.actions || []}
                      onChange={(e) => updateStage(idx, { actions: e.target.value })}
                      fullWidth
                    >
                      <MenuItem value={ACTION_SET_PROTECT_LOSS}>set_protect_loss</MenuItem>
                      <MenuItem value={ACTION_SET_DYNAMIC_LOSS}>set_dynamic_loss</MenuItem>
                    </Select>
                  </Box>
                ) : null}
              </Stack>
              <IconButton size="small" color="error" onClick={() => removeStage(idx)}>
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            </Stack>
          </Box>
        ))}
        {stages.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            暂无阶段，请点击“新增阶段”。
          </Typography>
        ) : null}
      </Stack>
    </Paper>
  );
}

function GoalSettingsEditor({ value, onChange }) {
  const goal = useMemo(() => normalizeGoal(value), [value]);

  const emit = (nextGoal) => {
    if (!onChange) return;
    onChange(sanitizeGoalByActions(nextGoal));
  };

  return (
    <Stack spacing={1.25}>
      <Paper variant="outlined" sx={{ p: 1.25 }}>
        <Typography fontWeight={600} sx={{ mb: 1 }}>
          到期设置
        </Typography>
        <Stack spacing={1}>
          <TextField
            size="small"
            label="到期窗口天数"
            type="number"
            value={goal.expiration.fixed_window_in_days}
            onChange={(e) => {
              emit({
                ...goal,
                expiration: {
                  ...goal.expiration,
                  fixed_window_in_days: toNumberOrEmpty(e.target.value),
                },
              });
            }}
            fullWidth
          />
          <Stack direction="row" spacing={1} alignItems="center">
            <Switch
              size="small"
              checked={Boolean(goal.expiration.is_trading_days)}
              onChange={(e) => {
                emit({
                  ...goal,
                  expiration: {
                    ...goal.expiration,
                    is_trading_days: e.target.checked,
                  },
                });
              }}
            />
            <Typography variant="body2">按交易日计数</Typography>
          </Stack>
        </Stack>
      </Paper>

      <StageEditor
        title="止损阶段（stop_loss.stages）"
        stages={goal.stop_loss.stages}
        onChange={(nextStages) => {
          emit({
            ...goal,
            stop_loss: {
              ...goal.stop_loss,
              stages: nextStages,
            },
          });
        }}
      />

      <StageEditor
        title="止盈阶段（take_profit.stages）"
        stages={goal.take_profit.stages}
        enableActions
        onChange={(nextStages) => {
          emit({
            ...goal,
            take_profit: {
              ...goal.take_profit,
              stages: nextStages,
            },
          });
        }}
      />

      {goal.protect_loss ? (
        <Paper variant="outlined" sx={{ p: 1.25 }}>
          <Typography fontWeight={600} sx={{ mb: 1 }}>
            保本止损（protect_loss）
          </Typography>
          <Stack spacing={1}>
            <TextField
              size="small"
              label="回撤到本金比例"
              type="number"
              value={goal.protect_loss.ratio}
              onChange={(e) => {
                emit({
                  ...goal,
                  protect_loss: {
                    ...goal.protect_loss,
                    ratio: toNumberOrEmpty(e.target.value),
                  },
                });
              }}
              fullWidth
              inputProps={{ step: '0.01' }}
              helperText="支持小数，例如 0.02 表示达到保本目标后回撤 2% 清仓。"
            />
            <Typography variant="body2" color="text.secondary">
              触发后固定清仓（不可修改）
            </Typography>
          </Stack>
        </Paper>
      ) : null}

      {goal.dynamic_loss ? (
        <Paper variant="outlined" sx={{ p: 1.25 }}>
          <Typography fontWeight={600} sx={{ mb: 1 }}>
            动态止损（dynamic_loss）
          </Typography>
          <Stack spacing={1}>
            <TextField
              size="small"
              label="可承受最大回撤比例"
              type="number"
              value={goal.dynamic_loss.ratio}
              onChange={(e) => {
                emit({
                  ...goal,
                  dynamic_loss: {
                    ...goal.dynamic_loss,
                    ratio: toNumberOrEmpty(e.target.value),
                  },
                });
              }}
              fullWidth
            />
            <Stack direction="row" spacing={1} alignItems="center">
              <Switch
                size="small"
                checked={Boolean(goal.dynamic_loss.close_invest)}
                onChange={(e) => {
                  emit({
                    ...goal,
                    dynamic_loss: {
                      ...goal.dynamic_loss,
                      close_invest: e.target.checked,
                    },
                  });
                }}
              />
              <Typography variant="body2">触发清仓</Typography>
            </Stack>
          </Stack>
        </Paper>
      ) : null}

      <Divider />
      <Typography variant="caption" color="text.secondary">
        规则：当 take_profit 的 actions 不再包含 set_protect_loss / set_dynamic_loss 时，会自动移除对应配置块。
      </Typography>
    </Stack>
  );
}

export default GoalSettingsEditor;
