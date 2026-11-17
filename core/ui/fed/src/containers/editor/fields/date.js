import React from 'react';
import { Date } from 'ui';
import { getByPath, runFieldEvents, setByPath } from '../editor.helper';
import EditorFieldLabel from './editorFieldLabel';
import './style.scss';

function DateField({ field, value, errors, onChange, emitChangeMeta, context = {} }) {
  if (typeof field?.visibleWhen === 'function' && !field.visibleWhen({ values: value })) {
    return null;
  }
  const current = getByPath(value, field.name);
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

  return (
    <div key={field.name} className="ntq-editor-input-field">
      <EditorFieldLabel field={field} context={context} />
      <Date
        labelPlacement="none"
        maxWidth={false}
        value={current || ''}
        onChange={(e) => applyChange(e.target.value)}
        disabled={isReadonly}
        error={fieldError || undefined}
        aria-label={field.label || field.name || '日期'}
      />
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

export default DateField;
