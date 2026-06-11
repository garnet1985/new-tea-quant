import React from 'react';
import PropTypes from 'prop-types';
import { Stack, Typography } from '@mui/material';
import { splitStrategyDescription } from '../../utils/formatStrategyDescription';

function StrategyDescriptionText({
  text,
  variant,
  color,
  className,
  empty,
  maxLines,
  component,
}) {
  const lines = splitStrategyDescription(text);
  const clampSx = maxLines != null && maxLines > 0
    ? {
      display: '-webkit-box',
      WebkitLineClamp: maxLines,
      WebkitBoxOrient: 'vertical',
      overflow: 'hidden',
    }
    : undefined;

  if (!lines.length) {
    if (empty == null || empty === '') return null;
    return (
      <Typography variant={variant} color={color} className={className} component={component} sx={clampSx}>
        {empty}
      </Typography>
    );
  }

  if (lines.length === 1) {
    return (
      <Typography variant={variant} color={color} className={className} component={component} sx={clampSx}>
        {lines[0]}
      </Typography>
    );
  }

  return (
    <Stack spacing={0.35} className={className} component={component}>
      {lines.map((line, idx) => (
        <Typography key={`${idx}-${line}`} variant={variant} color={color} sx={clampSx}>
          {line}
        </Typography>
      ))}
    </Stack>
  );
}

StrategyDescriptionText.propTypes = {
  text: PropTypes.oneOfType([PropTypes.string, PropTypes.number]),
  variant: PropTypes.string,
  color: PropTypes.string,
  className: PropTypes.string,
  empty: PropTypes.node,
  maxLines: PropTypes.number,
  component: PropTypes.elementType,
};

StrategyDescriptionText.defaultProps = {
  text: '',
  variant: 'body2',
  color: 'text.secondary',
  className: '',
  empty: '—',
  maxLines: null,
  component: 'div',
};

export default StrategyDescriptionText;
