import React from 'react';
import {
  ColumnsField,
  DateField,
  DateRangeField,
  DictParserField,
  FieldCollectionField,
  FieldGroupField,
  FeesOverrideField,
  InputField,
  SectionField,
  SelectField,
  SwitchField,
} from './fields';

function renderNode(node, value, onChange, errors, emitChangeMeta, context) {
  if (!node) return null;
  if (node.type === 'section') {
    return <SectionField node={node} value={value} onChange={onChange} errors={errors} emitChangeMeta={emitChangeMeta} renderNode={renderNode} context={context} />;
  }

  if (node.type === 'fieldGroup') {
    return <FieldGroupField node={node} value={value} onChange={onChange} errors={errors} emitChangeMeta={emitChangeMeta} renderNode={renderNode} context={context} />;
  }

  if (node.type === 'columns') {
    return <ColumnsField node={node} value={value} onChange={onChange} errors={errors} emitChangeMeta={emitChangeMeta} renderNode={renderNode} context={context} />;
  }

  if (node.type === 'dateRange') {
    return <DateRangeField field={node} value={value} onChange={onChange} errors={errors} emitChangeMeta={emitChangeMeta} />;
  }

  if (node.type === 'dictParser') {
    return <DictParserField field={node} value={value} onChange={onChange} errors={errors} emitChangeMeta={emitChangeMeta} context={context} />;
  }

  if (node.type === 'fieldCollection') {
    return <FieldCollectionField field={node} value={value} onChange={onChange} errors={errors} emitChangeMeta={emitChangeMeta} />;
  }

  if (node.type === 'feesOverride') {
    return <FeesOverrideField field={node} value={value} onChange={onChange} errors={errors} emitChangeMeta={emitChangeMeta} />;
  }

  if (node.type === 'switch') {
    return <SwitchField field={node} value={value} onChange={onChange} errors={errors} emitChangeMeta={emitChangeMeta} />;
  }

  if (node.type === 'date') {
    return <DateField field={node} value={value} onChange={onChange} errors={errors} emitChangeMeta={emitChangeMeta} />;
  }

  if (node.type === 'select') {
    return <SelectField field={node} value={value} onChange={onChange} errors={errors} emitChangeMeta={emitChangeMeta} />;
  }

  return <InputField field={node} value={value} onChange={onChange} errors={errors} emitChangeMeta={emitChangeMeta} />;
}

function Editor({
  schema,
  value,
  onChange,
  errors = {},
  onValueChange,
  onValidate,
  onValidationChange,
  context = {},
}) {
  const emitChangeMeta = (nextValue, meta) => {
    if (onValueChange) onValueChange(nextValue, meta);
    if (onValidate) {
      const nextErrors = onValidate(nextValue, meta) || {};
      if (onValidationChange) onValidationChange(nextErrors);
    }
  };

  return renderNode(schema, value || {}, onChange, errors, emitChangeMeta, context);
}

export default Editor;