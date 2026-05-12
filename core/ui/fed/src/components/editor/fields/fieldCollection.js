import React from 'react';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import AddIcon from '@mui/icons-material/Add';
import {
  Box,
  Button,
  IconButton,
  MenuItem,
  Paper,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { getByPath, setByPath } from '../editor.helper';

function isVisible(config, item, index, items) {
  if (typeof config?.visibleWhen !== 'function') return true;
  return Boolean(config.visibleWhen({ item, index, items }));
}

function parseItemValue(config, rawValue, item) {
  if (typeof config?.parse === 'function') return config.parse(rawValue, item);
  if (config?.type === 'number') {
    if (rawValue === '') return '';
    const n = Number(rawValue);
    return Number.isNaN(n) ? '' : n;
  }
  return rawValue;
}

function FieldCollectionField({ field, value, onChange, emitChangeMeta }) {
  if (typeof field?.visibleWhen === 'function' && !field.visibleWhen({ values: value })) {
    return null;
  }

  const items = Array.isArray(getByPath(value, field.name)) ? getByPath(value, field.name) : [];
  const template = Array.isArray(field.template) ? field.template : [];
  const allowedActions = Array.isArray(field.allowedActions)
    ? field.allowedActions
    : ['add', 'remove', 'edit'];
  const canAdd = allowedActions.includes('add');
  const canRemove = allowedActions.includes('remove');
  const canEdit = allowedActions.includes('edit');
  const emit = (nextItems, meta) => {
    if (!onChange) return;
    const updated = setByPath(value, field.name, nextItems);
    onChange(updated);
    if (emitChangeMeta) emitChangeMeta(updated, { name: field.name, value: nextItems, ...meta });
  };

  const updateItem = (index, patch) => {
    const nextItems = [...items];
    nextItems[index] = { ...nextItems[index], ...patch };
    emit(nextItems, { changedKey: 'update', index });
  };

  const removeItem = (index) => {
    const nextItems = items.filter((_, i) => i !== index);
    emit(nextItems, { changedKey: 'remove', index });
  };

  const addItem = () => {
    if (!canAdd) return;
    let nextItem = {};
    if (typeof field.initValue === 'function') {
      nextItem = field.initValue();
    } else if (field.initValue && typeof field.initValue === 'object') {
      nextItem = { ...field.initValue };
    }
    emit([...items, nextItem], { changedKey: 'add' });
  };

  return (
    <Paper variant="outlined" sx={{ p: 1.25 }}>
      <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1 }}>
        <Typography fontWeight={600}>{field.label}</Typography>
        <Button size="small" startIcon={<AddIcon />} onClick={addItem} disabled={!canAdd}>
          {field.addLabel || '新增'}
        </Button>
      </Stack>

      <Stack spacing={1}>
        {items.map((item, index) => (
          <Box key={`${field.name}-${index}`} sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1 }}>
            <Stack direction="row" spacing={1} alignItems="flex-start">
              <Stack spacing={1} sx={{ flex: 1 }}>
                {template.map((itemField) => {
                  if (!isVisible(itemField, item, index, items)) return null;
                  const current = item[itemField.key];

                  if (itemField.type === 'switch') {
                    return (
                      <Stack key={itemField.key} direction="row" spacing={1} alignItems="center">
                        <Box
                          component="input"
                          type="checkbox"
                          checked={Boolean(current)}
                          disabled={!canEdit}
                          onChange={(e) => updateItem(index, { [itemField.key]: e.target.checked })}
                        />
                        <Typography variant="body2">{itemField.label}</Typography>
                      </Stack>
                    );
                  }

                  if (itemField.type === 'select') {
                    return (
                      <Box key={itemField.key}>
                        <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
                          {itemField.label}
                        </Typography>
                        <Select
                          size="small"
                          multiple={Boolean(itemField.multiple)}
                          value={current || (itemField.multiple ? [] : '')}
                          disabled={!canEdit}
                          onChange={(e) => updateItem(index, { [itemField.key]: e.target.value })}
                          fullWidth
                        >
                          {(itemField.options || []).map((opt) => (
                            <MenuItem key={opt.value} value={opt.value}>
                              {opt.label}
                            </MenuItem>
                          ))}
                        </Select>
                      </Box>
                    );
                  }

                  return (
                    <TextField
                      key={itemField.key}
                      size="small"
                      label={itemField.label}
                      type={itemField.type === 'number' ? 'number' : 'text'}
                      value={current ?? ''}
                      InputProps={{ readOnly: !canEdit }}
                      disabled={!canEdit}
                      onChange={(e) => {
                        const next = parseItemValue(itemField, e.target.value, item);
                        updateItem(index, { [itemField.key]: next });
                      }}
                      fullWidth
                    />
                  );
                })}
              </Stack>

              <IconButton size="small" color="error" onClick={() => removeItem(index)} disabled={!canRemove}>
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            </Stack>
          </Box>
        ))}
        {items.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {field.emptyText || `暂无${field.label || '数据'}，请点击“${field.addLabel || '新增'}”。`}
          </Typography>
        ) : null}
      </Stack>
    </Paper>
  );
}

export default FieldCollectionField;
