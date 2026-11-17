import React from 'react';
import { Switch } from 'ui';
import { getByPath, runFieldEvents, setByPath } from '../editor.helper';
import EditorFieldLabel from './editorFieldLabel';
import './style.scss';

function SwitchField({ field, value, onChange, emitChangeMeta, context = {} }) {
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

  return (
    <div
      key={field.name}
      className="ntq-editor-field-collection__switch-row"
    >
      <EditorFieldLabel
        field={field}
        context={context}
        tooltipTitle={field.tooltip || field.description}
        noMargin
      />
      <Switch
        checked={Boolean(current)}
        onChange={(e) => applyChange(e.target.checked)}
        disabled={isReadonly}
        aria-label={field.label || field.name || '开关'}
      />
    </div>
  );
}

export default SwitchField;
