import React, { useEffect, useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { Link, Stack, Typography } from '@mui/material';
import { getMlExtrasStatus } from '../../../api/setupApi';
import { SettingsSchemaEditor } from '../../strategyWorkbenchPage/panels/strategySettingsPanel/settingsEditorSections';
import { buildStrategyAnalysisSchema } from '../../strategyWorkbenchPage/panels/strategySettingsPanel/editorSchemas/strategyAnalysis';

function StrategyDesignAnalysisSettings({ settings, onSettingsChange, context }) {
  const [mlInstalled, setMlInstalled] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getMlExtrasStatus()
      .then((status) => {
        if (!cancelled) setMlInstalled(Boolean(status?.installed));
      })
      .catch(() => {
        if (!cancelled) setMlInstalled(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const canToggle = mlInstalled === true;
  const schema = useMemo(
    () => buildStrategyAnalysisSchema({ mlInstalled: canToggle }),
    [canToggle],
  );

  return (
    <Stack spacing={1}>
      <SettingsSchemaEditor
        schema={schema}
        value={settings}
        onChange={onSettingsChange}
        context={context}
      />
      {mlInstalled === false ? (
        <Typography variant="caption" color="text.secondary" component="p">
          未安装机器学习依赖，无法更改此开关。可到
          {' '}
          <Link component={RouterLink} to="/settings/system" underline="hover">
            设置 → 安装与维护
          </Link>
          {' '}
          补装后再开关。
        </Typography>
      ) : null}
    </Stack>
  );
}

export default StrategyDesignAnalysisSettings;
