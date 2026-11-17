import React from 'react';
import { Button, Select, Switch, TextField } from 'ui';
import EditorFieldLabel from './editorFieldLabel';
import { getByPath, setByPath } from '../editor.helper';
import './style.scss';

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

function resolveDisplayValue(itemField, item, index, items) {
  if (typeof itemField?.resolve === 'function') {
    return itemField.resolve({ item, index, items });
  }
  return item?.[itemField.key] ?? '';
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
        <div key={itemField.key} className="ntq-editor-field-collection__switch-row">
          <EditorFieldLabel field={labelField} context={context} noMargin />
          <Switch
            checked={Boolean(current)}
            disabled={fieldDisabled}
            onChange={(e) => updateItem(index, { [itemField.key]: e.target.checked })}
            aria-label={itemField.label || itemField.key}
          />
        </div>
      );
    }

    if (itemField.type === 'display') {
      const displayText = resolveDisplayValue(itemField, item, index, items);
      const showEmpty = displayText === '' || displayText == null;
      return (
        <div key={itemField.key} className="ntq-editor-field-collection__field">
          <EditorFieldLabel field={labelField} context={context} />
          <TextField
            labelPlacement="none"
            maxWidth={false}
            value={showEmpty ? '' : String(displayText)}
            placeholder={itemField.placeholder || ' '}
            disabled
            className={[
              'ntq-editor-field-collection__display',
              showEmpty ? 'is-empty' : '',
            ].filter(Boolean).join(' ')}
            aria-label={itemField.label || itemField.key}
          />
        </div>
      );
    }

    if (itemField.type === 'select') {
      const options = itemField.options || [];
      const emptyOption = options.find((opt) => opt.value === '' || opt.value == null);
      const selectValue = itemField.multiple
        ? (Array.isArray(current) ? current : [])
        : (current ?? '');

      return (
        <div key={itemField.key} className="ntq-editor-field-collection__field">
          <EditorFieldLabel field={labelField} context={context} />
          <Select
            labelPlacement="none"
            maxWidth={false}
            multiple={Boolean(itemField.multiple)}
            displayEmpty={Boolean(emptyOption) && !itemField.multiple}
            value={selectValue}
            disabled={fieldDisabled}
            onChange={(e) => updateItem(index, { [itemField.key]: e.target.value })}
            options={options.map((opt) => ({
              value: opt.value,
              label: opt.label,
              disabled: Boolean(opt.disabled),
            }))}
            aria-label={itemField.label || itemField.key}
          />
        </div>
      );
    }

    return (
      <div key={itemField.key} className="ntq-editor-field-collection__field">
        <EditorFieldLabel field={labelField} context={context} />
        <TextField
          labelPlacement="none"
          maxWidth={false}
          type={itemField.type === 'number' ? 'number' : 'text'}
          value={current ?? ''}
          disabled={fieldDisabled}
          onChange={(e) => {
            const next = parseItemValue(itemField, e.target.value, item);
            updateItem(index, { [itemField.key]: next });
          }}
          aria-label={itemField.label || itemField.key}
        />
      </div>
    );
  });

  const rootClass = [
    'ntq-editor-field-collection',
    embedded ? 'ntq-editor-field-collection--embedded' : '',
  ].filter(Boolean).join(' ');

  return (
    <div className={rootClass}>
      <div className="ntq-editor-field-collection__body">
        {showHeaderLabel ? (
          <div className="ntq-editor-field-collection__heading">{field.label}</div>
        ) : null}

        <div className="ntq-editor-field-collection__toolbar">
          <Button
            variant="glass"
            icon="add"
            iconSize="sm"
            onClick={addItem}
            disabled={!canAdd}
          >
            {addLabel}
          </Button>
        </div>

        {items.length > 0 ? (
          <div className="ntq-editor-field-collection__items">
            {items.map((item, index) => (
              <div
                key={`${field.name}-${index}`}
                className="ntq-editor-field-collection__card"
              >
                <div className="ntq-editor-field-collection__card-fields">
                  {renderItemFields(item, index)}
                </div>
                {canRemove ? (
                  <div className="ntq-editor-field-collection__card-actions">
                    <Button
                      variant="danger"
                      icon="delete"
                      iconSize="sm"
                      onClick={() => removeItem(index)}
                      disabled={!canRemove}
                    >
                      {removeLabel}
                    </Button>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        ) : (
          <p className="ntq-muted ntq-editor-field-collection__empty">
            {field.emptyText || `暂无阶段目标，请点击「${addLabel}」。`}
          </p>
        )}
      </div>
    </div>
  );
}

export default React.memo(FieldCollectionField);
