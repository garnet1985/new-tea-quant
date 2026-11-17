import React from 'react';
import PropTypes from 'prop-types';
import './style.scss';

function clipTitle(lines) {
  return lines.length ? lines.join('\n') : '';
}

function MetaClipColumn({ label, lines, empty }) {
  const items = Array.isArray(lines)
    ? lines.map((item) => String(item || '').trim()).filter(Boolean)
    : [];
  const full = clipTitle(items);
  const body = items.length ? items : [empty];

  return (
    <div className="ntq-meta-clip-col">
      <span className="ntq-meta-clip-col__label">{label}</span>
      <div
        className="ntq-meta-clip-col__body"
        title={full || undefined}
      >
        {body.join('\n')}
      </div>
    </div>
  );
}

function StrategyMetaDetailText({
  entryConditions = [],
  goalLines = [],
  className = '',
  empty = '暂无',
}) {
  const entries = Array.isArray(entryConditions)
    ? entryConditions.map((item) => String(item || '').trim()).filter(Boolean)
    : [];
  const goals = Array.isArray(goalLines)
    ? goalLines.map((item) => String(item || '').trim()).filter(Boolean)
    : [];

  return (
    <div className={`ntq-meta-clip ${className}`.trim()}>
      <MetaClipColumn label="入场条件" lines={entries} empty={empty} />
      <MetaClipColumn label="目标" lines={goals} empty={empty} />
    </div>
  );
}

StrategyMetaDetailText.propTypes = {
  entryConditions: PropTypes.arrayOf(PropTypes.string),
  goalLines: PropTypes.arrayOf(PropTypes.string),
  className: PropTypes.string,
  empty: PropTypes.string,
};

export default StrategyMetaDetailText;
