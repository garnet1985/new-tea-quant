import React from 'react';
import './style.scss';

function ColumnsNode({ node, value, onChange, errors, emitChangeMeta, renderNode, context }) {
  const children = Array.isArray(node.children) ? node.children : [];
  const columns = Number(node.columns) || 1;
  const spans = Array.isArray(node.spans) ? node.spans : [];

  return (
    <div
      key={node.name}
      className="ntq-editor-columns"
      style={{ '--ntq-editor-columns': Math.max(1, columns) }}
    >
      {children.map((child, index) => (
        <div
          key={child.name || `${node.name}-${index}`}
          className="ntq-editor-columns__cell"
          style={spans[index] ? { '--ntq-editor-col-span': spans[index] } : undefined}
        >
          {renderNode(child, value, onChange, errors, emitChangeMeta, context)}
        </div>
      ))}
    </div>
  );
}

export default ColumnsNode;
