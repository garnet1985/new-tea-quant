import React from 'react';
import { Box, Card, CardContent, Chip, Stack, Typography } from '@mui/material';

/**
 * 导航中尚未实装的入口页：全宽由 MainLayout 的 main 已套 ntq-content-inner
 */
function ComingSoonPage({ title, description }) {
  return (
    <Box className="coming-soon-page" sx={{ p: 2, width: '100%' }}>
      <Card variant="outlined">
        <CardContent>
          <Stack spacing={1.5}>
            <Stack direction="row" alignItems="center" flexWrap="wrap" gap={1.5}>
              <Typography component="h1" variant="h5" fontWeight={700}>
                {title}
              </Typography>
              <Chip size="small" color="default" label="Coming soon" variant="outlined" />
            </Stack>
            <Typography color="text.secondary" variant="body1">
              {description || '该功能正在规划中，即将与桌面端工作流对接。'}
            </Typography>
            <Typography color="text.secondary" variant="body2" component="p" sx={{ fontStyle: 'italic' }}>
              This feature is not available yet — we&apos;re working on it.
            </Typography>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}

export default ComingSoonPage;
