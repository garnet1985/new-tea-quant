import React from 'react';
import { Checkbox } from 'ui';
import { getByPath, runFieldEvents, setByPath } from '../editor.helper';
import EditorFieldLabel from './editorFieldLabel';
import './style.scss';

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
    <div key={field.name} className="ntq-editor-checkbox-group">
      <EditorFieldLabel field={field} context={context} />
      <div className="ntq-editor-checkbox-group__list" role="group">
        {options.map((item) => {
          const tag = String(item?.value || '').trim().toLowerCase();
          if (!tag) return null;
          return (
            <span key={tag} title={item.tooltip || undefined}>
              <Checkbox
                label={item.label || tag}
                checked={selected.has(tag)}
                disabled={isReadonly}
                onChange={(e) => toggle(tag, e.target.checked)}
              />
            </span>
          );
        })}
      </div>
      {field.description && !field.tooltip ? (
        <p className="ntq-editor-input-field__hint ntq-muted">
          {field.description}
        </p>
      ) : null}
    </div>
  );
}

export default CheckboxGroupField;
