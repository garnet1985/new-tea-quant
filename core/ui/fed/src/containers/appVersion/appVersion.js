import React from 'react';
import AppVersionMark from 'views/appVersion';
import { useAppVersion } from './useAppVersion';

function AppVersion() {
  const label = useAppVersion();
  return <AppVersionMark label={label} />;
}

export default AppVersion;
