import React from 'react';
import { Card, CardContent, Container, Typography } from '@mui/material';

function PlaceholderPage({ title, description }) {
  return (
    <Container maxWidth="lg" sx={{ py: 5 }}>
      <Card variant="outlined">
        <CardContent>
          <Typography variant="h4" fontWeight={700}>
            {title}
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            {description}
          </Typography>
        </CardContent>
      </Card>
    </Container>
  );
}

export default PlaceholderPage;
