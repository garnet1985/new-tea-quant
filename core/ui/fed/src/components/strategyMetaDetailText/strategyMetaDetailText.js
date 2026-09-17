import React from 'react';
import PropTypes from 'prop-types';
import { Box, Tooltip, Typography } from '@mui/material';
import './strategyMetaDetailText.scss';

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
    <Box className="ntq-meta-clip-col">
      <Typography className="ntq-meta-clip-col__label" variant="caption">
        {label}
      </Typography>
      <Tooltip
        title={full ? (
          <Box className="ntq-meta-clip-col__tip">{full}</Box>
        ) : ''}
        placement="bottom-start"
        disableHoverListener={!full}
      >
        <Box className="ntq-meta-clip-col__body">
          {body.join('\n')}
        </Box>
      </Tooltip>
    </Box>
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
    <Box className={`ntq-meta-clip ${className}`.trim()}>
      <MetaClipColumn label="入场条件" lines={entries} empty={empty} />
      <MetaClipColumn label="目标" lines={goals} empty={empty} />
    </Box>
  );
}

StrategyMetaDetailText.propTypes = {
  entryConditions: PropTypes.arrayOf(PropTypes.string),
  goalLines: PropTypes.arrayOf(PropTypes.string),
  className: PropTypes.string,
  empty: PropTypes.string,
};

export default StrategyMetaDetailText;
