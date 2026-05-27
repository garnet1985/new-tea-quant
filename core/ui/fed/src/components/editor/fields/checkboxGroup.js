import React from 'react';
import {
  Checkbox,
  FormControlLabel,
  FormGroup,
  Typography,
} from '@mui/material';
import { getByPath, runFieldEvents, setByPath } from '../editor.helper';
import EditorFieldLabel from './editorFieldLabel';

function normalizeSelected(raw) {
  if (!Array.isArray(raw)) return [];
  return raw.map((item) => String(item || '').trim().toLowerCase()).filter(Boolean);
}

function CheckboxGroupField({ field, value, onChange, emitChangeMeta, context = {} }) {
  if (typeof field?.visibleWhen === 'function' && !field.visibleWhen({ values: value })) {
    return null;
  }
  const current = normalizeSelected(getByPath(value, field.name));
  const selected = new Set(current);
  const isReadonly = typeof field?.readonlyWhen === 'function'
    ? Boolean(field.readonlyWhen({ values: value }))
    : Boolean(field?.readonly);

  const options = field.options || [];

  const applyChange = (next) => {
    if (!onChange) return;
    let updated = setByPath(value, field.name, next);
    updated = runFieldEvents(updated, field, next);
    onChange(updated);
    if (emitChangeMeta) {
      emitChangeMeta(updated, { name: field.name, value: next });
    }
  };

  const toggle = (tag, checked) => {
    const nextSet = new Set(selected);
    if (checked) {
      nextSet.add(tag);
    } else {
      nextSet.delete(tag);
    }
    const ordered = options
      .map((item) => String(item?.value || '').trim().toLowerCase())
      .filter((tagValue) => tagValue && nextSet.has(tagValue));
    applyChange(ordered);
  };

  return (
    <div key={field.name}>
      <EditorFieldLabel field={field} context={context} />
      <FormGroup>
        {options.map((item) => {
          const tag = String(item?.value || '').trim().toLowerCase();
          if (!tag) return null;
          return (
            <FormControlLabel
              key={tag}
              control={(
                <Checkbox
                  size="small"
                  checked={selected.has(tag)}
                  disabled={isReadonly}
                  onChange={(e) => toggle(tag, e.target.checked)}
                />
              )}
              label={item.label || tag}
              title={item.tooltip || undefined}
            />
          );
        })}
      </FormGroup>
      {field.description && !field.tooltip ? (
        <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
          {field.description}
        </Typography>
      ) : null}
    </div>
  );
}

export default CheckboxGroupField;
