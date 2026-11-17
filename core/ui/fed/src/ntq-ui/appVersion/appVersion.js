import React from 'react';
import './style.scss';

/**
 * 顶栏版本号展示（纯展示；版本字符串由 container / hook 传入）。
 */
function AppVersion({ label, className = '', ...rest }) {
  if (!label) return null;
  const rootClass = ['ntq-app-version', className].filter(Boolean).join(' ');
  return (
    <span className={rootClass} {...rest}>
      {label}
    </span>
  );
}

export default AppVersion;
