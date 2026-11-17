import React from 'react';
import { TextArea, TextField } from 'ui';
import { getByPath, runFieldEvents, setByPath } from '../editor.helper';
import EditorFieldLabel from './editorFieldLabel';
import './style.scss';

function InputField({ field, value, errors, onChange, emitChangeMeta, context = {} }) {
  if (typeof field?.visibleWhen === 'function' && !field.visibleWhen({ values: value })) {
    return null;
  }
  const current = getByPath(value, field.name);
  const uiValue = typeof field.format === 'function'
    ? field.format(current, value)
    : (current ?? '');
  const fieldError = errors?.[field.name] || '';
  const isReadonly = typeof field?.readonlyWhen === 'function'
    ? Boolean(field.readonlyWhen({ values: value }))
    : Boolean(field?.readonly);

  const applyChange = (next) => {
    if (!onChange) return;
    let updated = setByPath(value, field.name, next);
    updated = runFieldEvents(updated, field, next);
    onChange(updated);
    if (emitChangeMeta) {
      emitChangeMeta(updated, { name: field.name, value: next });
    }
  };

  const helperBelow = fieldError
    || (field.description && !field.tooltip ? field.description : '')
    || '';

  const handleChange = (e) => {
    if (typeof field.parse === 'function') {
      applyChange(field.parse(e.target.value, value));
      return;
    }
    if (field.type === 'number') {
      const raw = e.target.value;
      if (raw === '') {
        applyChange('');
        return;
      }
      const n = Number(raw);
      applyChange(Number.isNaN(n) ? '' : n);
      return;
    }
    applyChange(e.target.value);
  };

  const shared = {
    labelPlacement: 'none',
    maxWidth: false,
    value: uiValue,
    error: fieldError || undefined,
    disabled: isReadonly,
    onChange: handleChange,
    placeholder: field.placeholder || '',
    'aria-label': field.label || field.name || '输入',
  };

  return (
    <div key={field.name} className="ntq-editor-input-field">
      <EditorFieldLabel field={field} context={context} />
      {field.multiline ? (
        <TextArea
          {...shared}
          rows={field.minRows || 4}
        />
      ) : (
        <TextField
          {...shared}
          type={field.type === 'number' ? 'number' : 'text'}
        />
      )}
      {helperBelow ? (
        <p
          className={[
            'ntq-editor-input-field__hint',
            fieldError ? 'is-error' : 'ntq-muted',
          ].filter(Boolean).join(' ')}
        >
          {helperBelow}
        </p>
      ) : null}
    </div>
  );
}

export default InputField;
