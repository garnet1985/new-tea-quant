import React from 'react';
import AppVersionMark from 'ntq-ui/appVersion';
import { useAppVersion } from './useAppVersion';

function AppVersion() {
  const label = useAppVersion();
  return <AppVersionMark label={label} />;
}

export default AppVersion;
