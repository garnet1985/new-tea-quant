import React from 'react';
import { Accordion } from 'ui';

function SectionField({ node, value, onChange, errors, emitChangeMeta, renderNode, context }) {
  const children = Array.isArray(node.children) ? node.children : [];
  const getChildKey = (child, index) => child?.name || child?.label || `${node.name || 'section'}-${index}`;

  return (
    <Accordion
      key={node.name}
      title={node.label}
      variant="nested"
      defaultExpanded={Boolean(node.defaultExpanded)}
      className="ntq-settings-sub-accordion"
    >
      <div className="ntq-editor-section__stack">
        {children.map((child, index) => (
          <React.Fragment key={getChildKey(child, index)}>
            {renderNode(child, value, onChange, errors, emitChangeMeta, context)}
          </React.Fragment>
        ))}
      </div>
    </Accordion>
  );
}

export default SectionField;
