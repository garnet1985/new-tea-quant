import React from 'react';
import NtqIcon from '../../ntqIcon/ntqIcon';
import EditorFieldLabel from './editorFieldLabel';
import {
  Box,
  Button,
  MenuItem,
  Paper,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from '@mui/material';
import { getByPath, setByPath } from '../editor.helper';

function isVisible(config, item, index, items) {
  if (typeof config?.visibleWhen !== 'function') return true;
  return Boolean(config.visibleWhen({ item, index, items }));
}

function isItemFieldDisabled(itemField, item, canEdit) {
  if (!canEdit) return true;
  if (typeof itemField?.readonlyWhen === 'function') {
    return Boolean(itemField.readonlyWhen({ item }));
  }
  if (typeof itemField?.disabledWhen === 'function') {
    return Boolean(itemField.disabledWhen({ item }));
  }
  return false;
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

function FieldCollectionField({ field, value, onChange, emitChangeMeta, context = {} }) {
  if (typeof field?.visibleWhen === 'function' && !field.visibleWhen({ values: value })) {
    return null;
  }

  const items = Array.isArray(getByPath(value, field.name)) ? getByPath(value, field.name) : [];
  const template = Array.isArray(field.template) ? field.template : [];
  const allowedActions = Array.isArray(field.allowedActions)
    ? field.allowedActions
    : ['add', 'remove', 'edit'];
  const canAddAllowed = allowedActions.includes('add');
  const canRemove = allowedActions.includes('remove');
  const canEdit = allowedActions.includes('edit');
  const hasCloseInvestStage = items.some((item) => Boolean(item?.close_invest));
  const canAdd = canAddAllowed && !hasCloseInvestStage;
  const addLabel = field.addLabel || '增加阶段目标';
  const removeLabel = field.removeLabel || '删除阶段目标';
  const showHeaderLabel = Boolean(field.label?.trim());
  const embedded = Boolean(field.embedded);

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

  const renderItemFields = (item, index) => template.map((itemField) => {
    if (!isVisible(itemField, item, index, items)) return null;
    const current = item[itemField.key];
    const fieldDisabled = isItemFieldDisabled(itemField, item, canEdit);
    const labelField = {
      label: itemField.label,
      tooltip: itemField.tooltip || '',
    };

    if (itemField.type === 'switch') {
      return (
        <Stack
          key={itemField.key}
          direction="row"
          justifyContent="space-between"
          alignItems="center"
        >
          <EditorFieldLabel field={labelField} context={context} sx={{ mb: 0 }} />
          <Switch
            size="small"
            checked={Boolean(current)}
            disabled={fieldDisabled}
            onChange={(e) => updateItem(index, { [itemField.key]: e.target.checked })}
          />
        </Stack>
      );
    }

    if (itemField.type === 'select') {
      const options = itemField.options || [];
      const emptyOption = options.find((opt) => opt.value === '' || opt.value == null);
      const selectValue = itemField.multiple
        ? (Array.isArray(current) ? current : [])
        : (current ?? (emptyOption ? '' : ''));
      const renderSelectValue = (selected) => {
        if (itemField.multiple) return selected;
        const matched = options.find((opt) => opt.value === selected);
        return matched?.label ?? selected;
      };

      return (
        <Box key={itemField.key}>
          <EditorFieldLabel field={labelField} context={context} />
          <Select
            size="small"
            multiple={Boolean(itemField.multiple)}
            displayEmpty={Boolean(emptyOption) && !itemField.multiple}
            value={selectValue}
            disabled={fieldDisabled}
            renderValue={renderSelectValue}
            onChange={(e) => updateItem(index, { [itemField.key]: e.target.value })}
            fullWidth
          >
            {options.map((opt) => (
              <MenuItem key={String(opt.value)} value={opt.value}>
                {opt.label}
              </MenuItem>
            ))}
          </Select>
        </Box>
      );
    }

    return (
      <Box key={itemField.key}>
        <EditorFieldLabel field={labelField} context={context} />
        <TextField
          size="small"
          type={itemField.type === 'number' ? 'number' : 'text'}
          value={current ?? ''}
          fullWidth
          disabled={fieldDisabled}
          onChange={(e) => {
            const next = parseItemValue(itemField, e.target.value, item);
            updateItem(index, { [itemField.key]: next });
          }}
        />
      </Box>
    );
  });

  const body = (
    <Stack spacing={1.25} alignItems="stretch">
      {showHeaderLabel ? (
        <Typography fontWeight={600}>{field.label}</Typography>
      ) : null}

      <Stack direction="row" justifyContent="flex-start">
        <Button
          size="small"
          variant="outlined"
          startIcon={<NtqIcon name="add" size={18} />}
          onClick={addItem}
          disabled={!canAdd}
        >
          {addLabel}
        </Button>
      </Stack>

      {items.length > 0 ? (
        <Stack spacing={1}>
          {items.map((item, index) => (
            <Box
              key={`${field.name}-${index}`}
              sx={{ border: 1, borderColor: 'divider', borderRadius: 1, p: 1.25 }}
            >
              <Stack spacing={1.5}>
                {renderItemFields(item, index)}
                {canRemove ? (
                  <Stack direction="row" justifyContent="flex-start" sx={{ pt: 0.25 }}>
                    <Button
                      size="small"
                      variant="outlined"
                      color="error"
                      startIcon={<NtqIcon name="delete" size={18} />}
                      onClick={() => removeItem(index)}
                      disabled={!canRemove}
                    >
                      {removeLabel}
                    </Button>
                  </Stack>
                ) : null}
              </Stack>
            </Box>
          ))}
        </Stack>
      ) : (
        <Typography variant="body2" color="text.secondary">
          {field.emptyText || `暂无阶段目标，请点击「${addLabel}」。`}
        </Typography>
      )}
    </Stack>
  );

  if (embedded) {
    return <Box className="ntq-editor-field-collection ntq-editor-field-collection--embedded">{body}</Box>;
  }

  return (
    <Paper variant="outlined" className="ntq-editor-field-collection" sx={{ p: 1.25 }}>
      {body}
    </Paper>
  );
}

export default React.memo(FieldCollectionField);
