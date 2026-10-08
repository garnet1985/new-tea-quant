import React from 'react';
import './style.scss';

function AppVersion({ label }) {
  if (!label) return null;
  return <span className="ntq-app-version">{label}</span>;
}

export default AppVersion;
