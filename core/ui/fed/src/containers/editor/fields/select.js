import React from 'react';
import { Select } from 'ui';
import { getByPath, runFieldEvents, setByPath } from '../editor.helper';
import EditorFieldLabel from './editorFieldLabel';
import './style.scss';

function SelectField({ field, value, onChange, emitChangeMeta, context = {} }) {
  if (typeof field?.visibleWhen === 'function' && !field.visibleWhen({ values: value })) {
    return null;
  }
  const current = getByPath(value, field.name);
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

  const options = field.options || [];
  const selectedOption = options.find((item) => item.value === current);
  const helperText = selectedOption?.tooltip
    || (field.description && !field.tooltip ? field.description : '');

  return (
    <div key={field.name} className="ntq-editor-select-field">
      <EditorFieldLabel field={field} context={context} />
      <Select
        labelPlacement="none"
        maxWidth={false}
        multiple={Boolean(field.multiple)}
        displayEmpty={false}
        value={current ?? (field.multiple ? [] : '')}
        onChange={(e) => applyChange(e.target.value)}
        disabled={isReadonly}
        options={options.map((item) => ({
          value: item.value,
          label: item.label,
          disabled: Boolean(item.disabled),
        }))}
        aria-label={field.label || field.name || '选择'}
      />
      {helperText ? (
        <p className="ntq-muted ntq-editor-select-field__hint">{helperText}</p>
      ) : null}
    </div>
  );
}

export default SelectField;
