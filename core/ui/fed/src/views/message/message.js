import React from 'react';
import { Alert } from '@mui/material';
import './style.scss';

function Message({
  severity = 'info',
  children,
  icon,
  onClose,
  className = '',
}) {
  const rootClass = ['ntq-message', `ntq-message--${severity}`, className].filter(Boolean).join(' ');
  return (
    <Alert
      severity={severity}
      icon={icon}
      onClose={onClose}
      className={rootClass}
    >
      {children}
    </Alert>
  );
}

export default Message;
