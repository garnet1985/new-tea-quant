import React from 'react';
import EditorFieldGroup from './editorFieldGroup';

function FieldGroupField({ node, value, onChange, errors, emitChangeMeta, renderNode, context }) {
  if (typeof node?.visibleWhen === 'function' && !node.visibleWhen({ values: value })) {
    return null;
  }

  const children = Array.isArray(node.children) ? node.children : [];
  const getChildKey = (child, index) => child?.name || child?.label || `${node.name || 'fieldGroup'}-${index}`;
  const hasLabel = Boolean(node.label?.trim());

  const childNodes = children.map((child, index) => (
    <React.Fragment key={getChildKey(child, index)}>
      {renderNode(child, value, onChange, errors, emitChangeMeta, context)}
    </React.Fragment>
  ));

  return (
    <EditorFieldGroup
      key={node.name}
      label={hasLabel ? node.label : undefined}
      tooltip={node.tooltip || node.labelTooltip || ''}
      context={context}
      plain={!hasLabel}
    >
      {childNodes}
    </EditorFieldGroup>
  );
}

export default FieldGroupField;
